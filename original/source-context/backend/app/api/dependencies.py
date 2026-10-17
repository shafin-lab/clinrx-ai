"""Application-scoped resources and replaceable synthetic-only dependencies."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from fastapi import Request
from sqlalchemy import Engine
from app.api.config import APIConfig, SyntheticScope
from app.api.review_commands import ExecutionCommandCodec, StateContextCodec
from app.api.schemas.common import DTO
from app.execution.patient_state_execution import GRANT_ACTOR, GRANT_TARGET
from app.models.clinical.governance import OutputTarget
from app.persistence.errors import RecordNotFound


class SyntheticAccessContext(DTO):
    scopes: tuple[SyntheticScope, ...]

    def require_scope(self, patient_id, encounter_id):
        if not any(s.patient_id == patient_id and s.encounter_id == encounter_id for s in self.scopes):
            raise RecordNotFound('not found')


class SyntheticIdentity(DTO):
    actor: str = GRANT_ACTOR
    target: OutputTarget = GRANT_TARGET


def real_clock():
    return datetime.now(timezone.utc)


def make_clock(config):
    if config.clock_mode == 'real':
        return real_clock
    # Fixed, explicitly configured scenario instant, not a persistence clock.
    at = config.simulation_at
    return lambda: at


@dataclass(frozen=True)
class ApplicationDependencies:
    config: APIConfig
    engine: Engine
    access: SyntheticAccessContext
    identity: SyntheticIdentity
    clock: Callable[[], datetime]
    state_context: StateContextCodec
    execution_command: ExecutionCommandCodec


def get_config(request: Request):
    return request.app.state.dependencies.config


def get_engine(request: Request):
    return request.app.state.dependencies.engine


def get_access_context(request: Request):
    return request.app.state.dependencies.access


def get_synthetic_identity(request: Request):
    return request.app.state.dependencies.identity


def get_workflow_clock(request: Request):
    return request.app.state.dependencies.clock


def get_state_context_codec(request: Request):
    return request.app.state.dependencies.state_context


def get_execution_command_codec(request: Request):
    return request.app.state.dependencies.execution_command
