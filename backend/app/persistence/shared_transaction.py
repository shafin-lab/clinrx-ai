"""One synchronous, local transaction for clinical facts and execution artifacts."""
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .database import require_schema
from .errors import PersistenceError, PersistenceInputError, SchemaMismatch, TransactionAborted, TransactionCompletionUnknown

if TYPE_CHECKING:
    from .repository import PatientRepository
    from .executions import _ExecutionAdapter
    from .creatinine_executions import _CreatinineExecutionAdapter
    from .patient_state_executions import _PatientStateExecutionAdapter
    from .micro_antimicrobial_executions import _MicroAntimicrobialExecutionAdapter


class _Lifecycle:
    """One authoritative state; failed units can only close, never recover."""

    def __init__(self, *, sanitize=False):
        self._state = 'active'
        self.sanitize = sanitize

    def check(self):
        if self._state != 'active':
            raise TransactionAborted('persistence transaction is closed or failed')

    def fail(self):
        if self._state == 'active':
            self._state = 'failed'

    def close(self):
        self._state = 'closed'


def _operation(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        state = self._lifecycle
        state.check()
        try:
            return method(self, *args, **kwargs)
        except (ValidationError, PydanticSerializationError):
            state.fail()
            raise PersistenceInputError(f'invalid domain input for {method.__name__}') from None
        except PersistenceError as error:
            state.fail()
            if state.sanitize:
                raise error from None
            raise
        except Exception:
            state.fail()
            if state.sanitize:
                raise TransactionAborted('persistence operation failed') from None
            raise
        except BaseException:
            state.fail()
            raise
    return checked


@dataclass(frozen=True)
class ExecutionTransaction:
    repository: 'PatientRepository'
    executions: '_ExecutionAdapter'
    creatinine_executions: '_CreatinineExecutionAdapter'
    patient_state_executions: '_PatientStateExecutionAdapter'
    micro_antimicrobial_executions: '_MicroAntimicrobialExecutionAdapter'


@contextmanager
def execution_transaction(engine: Engine):
    """Yield five adapters sharing one BEGIN IMMEDIATE and failure lifecycle.

    Results remain provisional until successful exit. Contexts never implicitly
    join; use these handles rather than nesting standalone persistence calls.
    Handles must remain in this synchronous thread/process and cannot be reused.
    """
    if not isinstance(engine, Engine):
        raise PersistenceInputError('execution transaction requires an Engine')
    # Local imports avoid a cycle through execution contracts and the repository.
    from .repository import PatientRepository
    from .executions import _ExecutionAdapter
    from .creatinine_executions import _CreatinineExecutionAdapter
    from .patient_state_executions import _PatientStateExecutionAdapter
    from .micro_antimicrobial_executions import _MicroAntimicrobialExecutionAdapter

    state = _Lifecycle(sanitize=True)
    body_error = None
    completing = False
    try:
        with Session(engine, expire_on_commit=False) as session:
            with session.begin():
                require_schema(session.connection())
                tx = ExecutionTransaction(PatientRepository(session, _lifecycle=state),
                                          _ExecutionAdapter(session, state),
                                          _CreatinineExecutionAdapter(session, state),
                                          _PatientStateExecutionAdapter(session, state),
                                          _MicroAntimicrobialExecutionAdapter(session, state))
                try:
                    yield tx
                except BaseException as error:
                    body_error = error
                    state.fail()
                    raise
                state.check()
                completing = True
    except Exception as error:
        # Preserve exceptions from caller code. Setup/cleanup/commit exceptions
        # originate inside this boundary and must not expose driver details.
        if error is body_error:
            raise
        if completing:
            raise TransactionCompletionUnknown('transaction completion could not be confirmed') from None
        if isinstance(error, SchemaMismatch):
            raise SchemaMismatch('execution storage requires the reviewed schema revision') from None
        if isinstance(error, PersistenceError):
            raise error from None
        raise TransactionAborted('persistence transaction failed') from None
    finally:
        state.close()
