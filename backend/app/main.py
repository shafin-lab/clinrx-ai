"""Existing ASGI entry point with explicit lifespan-owned application resources."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.config import APIConfig, load_config
from app.api.dependencies import ApplicationDependencies, SyntheticAccessContext, SyntheticIdentity, make_clock
from app.api.errors import install_error_handlers
from app.api.knowledge import router as knowledge_router
from app.api.middleware import BoundaryMiddleware, DevelopmentCORS
from app.api.review_commands import ExecutionCommandCodec, StateContextCodec
from app.api.routes.health import router as health_router
from app.persistence.database import create_database


def create_app(config: APIConfig | None = None, *, engine=None, clock=None, access=None,
               identity=None, state_context_codec=None, execution_command_codec=None):
    # Configuration is loaded at lifespan, not import. Supplied Engines remain caller-owned.
    @asynccontextmanager
    async def lifespan(application):
        settings = load_config() if config is None else APIConfig.model_validate(config)
        owned_engine = engine is None
        database = create_database(settings.database_path) if owned_engine else engine
        try:
            application.state.dependencies = ApplicationDependencies(settings, database,
                access if access is not None else SyntheticAccessContext(scopes=settings.synthetic_scopes),
                identity if identity is not None else SyntheticIdentity(),
                clock if clock is not None else make_clock(settings),
                state_context_codec if state_context_codec is not None else StateContextCodec(settings.envelope_signing_key),
                execution_command_codec if execution_command_codec is not None else ExecutionCommandCodec(settings.envelope_signing_key))
            yield
        finally:
            if owned_engine:
                database.dispose()
            if hasattr(application.state, 'dependencies'):
                del application.state.dependencies

    application = FastAPI(title='ClinRx AI', version='0.0.1', lifespan=lifespan)

    @application.get('/')
    def root():
        return {'application': 'ClinRx AI', 'version': '0.0.1', 'status': 'running'}

    application.include_router(knowledge_router)
    application.include_router(health_router)
    install_error_handlers(application)
    application.add_middleware(DevelopmentCORS)
    application.add_middleware(BoundaryMiddleware)
    return application


app = create_app()
