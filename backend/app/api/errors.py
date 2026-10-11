"""Allowlisted exception translation. Never stringify untrusted exceptions."""
from uuid import UUID, uuid4
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from app.api.review_commands import InvalidCommand, InvalidStateContext
from app.api.schemas.errors import APIError, FieldError
from app.api.schemas.temporal_review import CompletionUnknownResponse
from app.execution.patient_state_execution import PatientStateExecutionError
from app.execution.patient_state_inference import PatientStateTemporalInferenceError
from app.persistence.errors import (PersistenceInputError, QueryLimitExceeded, RecordConflict,
    RecordNotFound, SchemaMismatch, ScopeMismatch, StorageIntegrityError, TransactionAborted,
    TransactionCompletionUnknown, UnsupportedOperation)


class RequestTooLarge(Exception):
    pass


# Ordering is deliberate: completion uncertainty is a TransactionAborted subtype.
MAPPINGS = (
    (TransactionCompletionUnknown, 503, 'completion_unknown', 'Execution completion could not be confirmed.'),
    (TransactionAborted, 503, 'transaction_failed', 'The transaction could not be completed.'),
    (InvalidCommand, 422, 'invalid_command', 'Invalid execution command.'),
    (InvalidStateContext, 422, 'invalid_state_context', 'Invalid state context.'),
    (RecordNotFound, 404, 'not_found', 'Resource not found.'),
    (ScopeMismatch, 404, 'not_found', 'Resource not found.'),
    (RecordConflict, 409, 'execution_conflict', 'Execution request conflicts with retained content.'),
    (StorageIntegrityError, 500, 'storage_integrity_failure', 'Stored content failed integrity validation.'),
    (SchemaMismatch, 503, 'storage_unavailable', 'Storage is unavailable.'),
    (UnsupportedOperation, 422, 'unsupported_review_input', 'Unsupported review input.'),
    (PatientStateTemporalInferenceError, 422, 'unsupported_review_input', 'Unsupported review input.'),
    (QueryLimitExceeded, 422, 'bounded_view_limit_exceeded', 'The bounded resource limit was exceeded.'),
    (RequestTooLarge, 413, 'request_too_large', 'Request size limit exceeded.'),
    (PersistenceInputError, 422, 'invalid_request', 'Invalid request.'),
    (PatientStateExecutionError, 422, 'invalid_request', 'Invalid request.'),
    (RequestValidationError, 422, 'invalid_request', 'Invalid request.'),
    (ValidationError, 422, 'invalid_request', 'Invalid request.'),
)
SAFE_FIELDS = frozenset(('body', 'query', 'path', 'execution_id', 'command', 'state_context',
    'earlier_laboratory', 'later_laboratory', 'medication', 'reference', 'expected_digest',
    'kind', 'id', 'version', 'patient_id', 'encounter_id', 'review_start', 'review_end'))


def correlation(request):
    value = getattr(request.state, 'correlation_id', None)
    return value if isinstance(value, UUID) else uuid4()


def error_response(error, correlation_id, *, execution_id=None):
    status, code, message = 500, 'internal_error', 'Request could not be completed.'
    for kind, status_code, error_code, safe_message in MAPPINGS:
        if isinstance(error, kind):
            status, code, message = status_code, error_code, safe_message
            break
    if isinstance(error, HTTPException):
        status = error.status_code if error.status_code in (400, 404, 405, 413, 422, 503) else 500
        code, message = ('not_found', 'Resource not found.') if status == 404 else (
            ('method_not_allowed', 'Method not allowed.') if status == 405 else ('invalid_request', 'Invalid request.'))
    if isinstance(error, TransactionCompletionUnknown) and isinstance(execution_id, UUID):
        body = CompletionUnknownResponse(execution_id=execution_id, correlation_id=correlation_id)
    else:
        fields = []
        if isinstance(error, RequestValidationError):
            for item in error.errors()[:20]:
                path = '.'.join(p if isinstance(p, str) and p in SAFE_FIELDS else 'field' for p in item.get('loc', ()))
                raw_code = item.get('type')
                safe_code = raw_code if raw_code in ('missing', 'extra_forbidden', 'too_long') else 'invalid_value'
                fields.append(FieldError(path=path[:256], code=safe_code))
        body = APIError(code=code, message=message, correlation_id=correlation_id, fields=tuple(fields))
    return status, body


async def handle_error(request, error):
    cid = correlation(request)
    status, body = error_response(error, cid, execution_id=getattr(request.state, 'execution_id', None))
    request.state.error_code = getattr(body, 'code', getattr(body, 'status', 'internal_error'))
    headers = {'X-Correlation-ID': str(cid)}
    if getattr(request.state, 'no_store', False):
        headers['Cache-Control'] = 'no-store'
    return JSONResponse(status_code=status, content=body.model_dump(mode='json'), headers=headers)


def install_error_handlers(app):
    for kind, *_ in MAPPINGS:
        app.add_exception_handler(kind, handle_error)
    app.add_exception_handler(HTTPException, handle_error)
    app.add_exception_handler(Exception, handle_error)
