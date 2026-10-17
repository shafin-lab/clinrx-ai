"""Separate read-only synthetic gateway. Never used by the normal API entry point."""
import os
import secrets
from pathlib import Path
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from app.api.config import APIConfig
from app.demo.circulatory import SIMULATION_AT
from app.demo.comprehensive import RELEASED_ID, WITHHELD_ID
from app.main import create_app

PREFIX = '/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
LOOKUPS = {PREFIX + '/circulatory-reviews/' + str(id) for id in (RELEASED_ID, WITHHELD_ID)}


class SyntheticDemoGateway:
    """Allow only the comprehensive workspace's three read operations.

    History uses POST but does not append facts or receipts. All other API paths,
    documentation, legacy operations and filesystem paths are unavailable.
    """
    def __init__(self, database: Path, frontend: Path, signing_key: str):
        if not database.is_absolute() or not database.is_file():
            raise ValueError('existing absolute synthetic fixture database required')
        if not frontend.is_absolute() or not (frontend / 'index.html').is_file() or not (frontend / 'assets').is_dir():
            raise ValueError('existing absolute frontend build directory required')
        self.config = APIConfig(database_path=database, environment='local_synthetic_demo',
            envelope_signing_key=signing_key, clock_mode='historical_simulation',
            simulation_at=SIMULATION_AT, circulatory_execution_enabled=False)
        self.core = create_app(self.config)
        self.static = StaticFiles(directory=frontend, html=True, follow_symlink=False)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            return await self.core(scope, receive, send)
        if scope['type'] != 'http':
            return await send({'type': 'websocket.close', 'code': 1008})
        path, method = scope['path'], scope['method']

        async def protected_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', ()) if k.lower() != b'cache-control']
                headers += [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'), (b'x-frame-options', b'DENY'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]
                message = {**message, 'headers': headers}
            await send(message)

        api_read = (method == 'GET' and (path == PREFIX + '/patient-state-v3' or path in LOOKUPS))
        history_read = method == 'POST' and path == PREFIX + '/circulatory-evidence-history'
        if api_read or history_read:
            return await self.core(scope, receive, protected_send)
        if method == 'GET' and path == '/health':
            return await JSONResponse({'status': 'ok', 'mode': 'synthetic-read-only', 'execution_enabled': False})(scope, receive, protected_send)
        if method in ('GET', 'HEAD') and (path == '/' or path.startswith('/assets/')):
            # StaticFiles protects traversal. No source, database, manifest or SPA fallback.
            try:
                return await self.static(scope, receive, protected_send)
            except Exception as error:
                from starlette.exceptions import HTTPException
                if not isinstance(error, HTTPException) or error.status_code != 404:
                    raise
        return await JSONResponse({'code': 'not_found'}, status_code=404)(scope, receive, protected_send)


def from_environment():
    # Separate namespace: no production env loading, gate switch or inherited key.
    # One process owns the ephemeral state-context signing key. Startup never seeds.
    return SyntheticDemoGateway(Path(os.environ['CLINRX_SYNTHETIC_DATABASE']),
        Path(os.environ['CLINRX_SYNTHETIC_FRONTEND']), secrets.token_hex(32))
