"""Explicit local synthetic/test settings. No production mode or secret default."""
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import AwareDatetime, Field, SecretStr, field_validator, model_validator
from app.api.schemas.common import DTO, Identifier


class SyntheticScope(DTO):
    patient_id: Identifier
    encounter_id: Identifier


class APIConfig(DTO):
    database_path: Path
    environment: Literal['local_synthetic_demo', 'test']
    api_host: Literal['127.0.0.1', 'localhost', '::1'] = '127.0.0.1'
    api_port: int = Field(default=8000, strict=True, ge=1, le=65535)
    allowed_dev_origins: tuple[str, ...] = ()
    envelope_signing_key: SecretStr = Field(repr=False)
    clock_mode: Literal['real', 'historical_simulation'] = 'real'
    simulation_at: AwareDatetime | None = None
    max_review_window_seconds: int = Field(default=604800, strict=True, ge=1, le=31536000)
    max_response_bytes: int = Field(default=2097152, strict=True, ge=1024, le=16777216)
    synthetic_scopes: tuple[SyntheticScope, ...] = (SyntheticScope(patient_id='synthetic-p1', encounter_id='synthetic-e1'),)

    @field_validator('database_path')
    @classmethod
    def absolute_path(cls, value):
        if not value.is_absolute() or value.name in ('', ':memory:'):
            raise ValueError('absolute local database path required')
        return value

    @field_validator('envelope_signing_key')
    @classmethod
    def key(cls, value):
        if re.fullmatch(r'[0-9a-fA-F]{64}', value.get_secret_value()) is None:
            raise ValueError('require a configured 32-byte random hex key')
        return value

    @field_validator('allowed_dev_origins')
    @classmethod
    def origins(cls, values):
        for value in values:
            parsed = urlsplit(value)
            if (parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                    or parsed.username is not None or parsed.password is not None
                    or parsed.path or parsed.query or parsed.fragment or '*' in value
                    or value != value.strip() or any(c.isspace() for c in value)):
                raise ValueError('require exact loopback development origins')
            _ = parsed.port
            host = '[' + parsed.hostname + ']' if parsed.hostname == '::1' else parsed.hostname
            expected = parsed.scheme + '://' + host + (':' + str(parsed.port) if parsed.port is not None else '')
            if value != expected:
                raise ValueError('require exact development origin spelling')
        if len(set(values)) != len(values):
            raise ValueError('duplicate origins')
        return values

    @model_validator(mode='after')
    def explicit_clock(self):
        if (self.clock_mode == 'historical_simulation') != (self.simulation_at is not None):
            raise ValueError('historical simulation requires explicit time and mode')
        return self


def load_config():
    try:
        return APIConfig(database_path=os.environ['CLINRX_DATABASE_PATH'],
            environment=os.environ['CLINRX_ENVIRONMENT'],
            api_host=os.environ.get('CLINRX_API_HOST', '127.0.0.1'),
            api_port=int(os.environ.get('CLINRX_API_PORT', '8000')),
            allowed_dev_origins=tuple(filter(None, os.environ.get('CLINRX_ALLOWED_DEV_ORIGINS', '').split(','))),
            envelope_signing_key=os.environ['CLINRX_ENVELOPE_SIGNING_KEY'],
            clock_mode=os.environ.get('CLINRX_CLOCK_MODE', 'real'),
            simulation_at=os.environ.get('CLINRX_SIMULATION_AT'),
            max_review_window_seconds=int(os.environ.get('CLINRX_MAX_REVIEW_WINDOW_SECONDS', '604800')),
            max_response_bytes=int(os.environ.get('CLINRX_MAX_RESPONSE_BYTES', '2097152')))
    except Exception:
        raise RuntimeError('invalid ClinRx API configuration') from None
