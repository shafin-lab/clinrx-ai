"""Bounded error responses never contain exception text or submitted values."""
from typing import Literal
from uuid import UUID
from app.api.schemas.common import DTO

ErrorCode = Literal['invalid_request', 'unsupported_review_input', 'invalid_command',
    'invalid_state_context', 'not_found', 'execution_conflict', 'storage_integrity_failure',
    'storage_unavailable', 'transaction_failed', 'completion_unknown', 'request_too_large',
    'bounded_view_limit_exceeded', 'internal_error', 'method_not_allowed']


class FieldError(DTO):
    path: str
    code: Literal['missing', 'extra_forbidden', 'invalid_type', 'invalid_value', 'too_long']


class APIError(DTO):
    code: ErrorCode
    message: str
    correlation_id: UUID
    fields: tuple[FieldError, ...] = ()
