"""Correlation and bounded metadata only. No raw request/response logging."""
import logging
from time import perf_counter
from uuid import UUID, uuid4
from app.api.errors import RequestTooLarge, handle_error
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger('clinrx.api')
MAX_REQUEST_BYTES = 262144


async def no_store(request: Request):
    """Opt-in dependency for future clinical routes, including their errors."""
    request.state.no_store = True


class BoundaryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        state = scope.setdefault('state', {})
        cid = uuid4()  # Never reflect an arbitrary incoming correlation header.
        state['correlation_id'] = cid
        # Clinical prefix must be protected even before JSON/dependency validation.
        if scope.get('path', '').startswith('/api/v1/patients/'):
            state['no_store'] = True
        started, status = perf_counter(), 500
        response_started = False

        async def safe_send(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                response_started = True
                status = message['status']
                headers = list(message.get('headers', ()))
                headers = [(k, v) for k, v in headers if k.lower() != b'x-correlation-id']
                headers.append((b'x-correlation-id', str(cid).encode('ascii')))
                if state.get('no_store'):
                    headers = [(k, v) for k, v in headers if k.lower() != b'cache-control']
                    headers.append((b'cache-control', b'no-store'))
                message = {**message, 'headers': headers}
            await send(message)

        try:
            declared = [v for k, v in scope.get('headers', ()) if k.lower() == b'content-length']
            if declared and (len(declared) != 1 or len(declared[0]) > 10
                             or not declared[0].isdigit() or int(declared[0]) > MAX_REQUEST_BYTES):
                raise RequestTooLarge()
            # Bound actual bytes before FastAPI parses JSON or catches read errors.
            chunks, total = [], 0
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                total += len(chunk)
                if total > MAX_REQUEST_BYTES:
                    raise RequestTooLarge()
                chunks.append(chunk)
                if not message.get('more_body', False):
                    break
            consumed = False

            async def buffered_receive():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
                return await receive()

            await self.app(scope, buffered_receive, safe_send)
        except Exception as error:
            # Keep framework/server exception logging from exposing traceback inputs.
            if response_started:
                raise RuntimeError('response transmission failed') from None
            response = await handle_error(Request(scope), error)
            await response(scope, receive, safe_send)
        finally:
            route = scope.get('route')
            template = getattr(route, 'path', '<unmatched>')
            execution_id = state.get('execution_id')
            logger.info('request_complete', extra={'correlation_id': str(cid), 'route_template': template,
                'execution_id': str(execution_id) if isinstance(execution_id, UUID) else None,
                'outcome': state.get('error_code', str(status)),
                'duration_ms': round((perf_counter() - started) * 1000, 3)})


class DevelopmentCORS:
    """Resolve configured origins after lifespan; no mutable module singleton."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        config = scope['app'].state.dependencies.config
        middleware = CORSMiddleware(self.app, allow_origins=config.allowed_dev_origins,
            allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
            expose_headers=['X-Correlation-ID', 'X-ClinRx-Mode', 'X-ClinRx-Stage'])
        await middleware(scope, receive, send)
