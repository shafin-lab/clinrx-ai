"""Untimed authenticated envelopes. Integrity only, never resource authorization.

No compression, unsafe deserialization, expiry, clinical work or alternate clinical
canonicalizer. ItsDangerous performs HMAC; base64 is transport encoding only.
"""
import base64
from hashlib import sha256
from typing import Literal

from itsdangerous import Signer
from pydantic import SecretStr
from app.api.schemas.common import DTO, MAX_ENVELOPE_BYTES
from app.execution.patient_state import PatientStateScope
from app.execution.patient_state_execution import PatientStateTemporalExecutionRequest
from app.persistence.mapping import canonical_payload


class InvalidCommand(Exception):
    pass


class InvalidStateContext(Exception):
    pass


class StateContext(DTO):
    transport_version: Literal['1'] = '1'
    scope: PatientStateScope
    profile_id: Literal['SyntheticLaboratoryMedicationState'] = 'SyntheticLaboratoryMedicationState'
    profile_version: Literal['1'] = '1'
    selection_digest_version: Literal['1'] = '1'


class _Envelope:
    def __init__(self, key: SecretStr, purpose, model, error):
        from app.api.config import APIConfig
        # Same key requirements apply even when the codec is constructed directly.
        key = APIConfig.key(key)
        self._signer = Signer(bytes.fromhex(key.get_secret_value()),
            salt='clinrx.api.' + purpose + '.v1', key_derivation='hmac', digest_method=sha256)
        self._prefix = (purpose + '.v1.').encode('ascii')
        self._model, self._error = model, error

    def issue(self, value):
        try:
            if type(value) is not self._model:
                raise ValueError()
            value = self._model.model_validate(value)
            raw = canonical_payload(value).encode('utf-8')
            if len(raw) > MAX_ENVELOPE_BYTES:
                raise ValueError()
            encoded = base64.urlsafe_b64encode(raw)
            token = self._signer.sign(self._prefix + encoded).decode('ascii')
            if len(token) > MAX_ENVELOPE_BYTES:
                raise ValueError()
            return token
        except Exception:
            raise self._error('invalid envelope') from None

    def verify(self, token):
        try:
            if type(token) is not str or not 0 < len(token) <= MAX_ENVELOPE_BYTES:
                raise ValueError()
            signed = token.encode('ascii')
            payload = self._signer.unsign(signed)
            if not payload.startswith(self._prefix):
                raise ValueError()
            encoded = payload[len(self._prefix):]
            raw = base64.b64decode(encoded, altchars=b'-_', validate=True)
            if base64.urlsafe_b64encode(raw) != encoded:
                raise ValueError()
            value = self._model.model_validate_json(raw)
            if canonical_payload(value).encode('utf-8') != raw:
                raise ValueError()
            # Reject alternate signature spellings too; no time or randomized salt.
            if self._signer.sign(payload) != signed:
                raise ValueError()
            return value
        except Exception:
            raise self._error('invalid envelope') from None


class StateContextCodec(_Envelope):
    def __init__(self, key: SecretStr):
        super().__init__(key, 'state-context', StateContext, InvalidStateContext)


class ExecutionCommandCodec(_Envelope):
    def __init__(self, key: SecretStr):
        super().__init__(key, 'execution-command', PatientStateTemporalExecutionRequest, InvalidCommand)
