"""Migrations use the same SQLite connection/transaction policy as the repository."""
import os

from alembic import context

from app.persistence.database import create_database
from app.persistence.entities import Base

config = context.config


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata,
                      compare_type=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError('this initial SQLite migration requires an online connection')
elif config.attributes.get('connection') is not None:
    run(config.attributes['connection'])
else:
    path = os.environ.get('CLINRX_DATABASE_PATH')
    if not path:
        raise RuntimeError('set CLINRX_DATABASE_PATH to a local synthetic database file')
    engine = create_database(path)
    try:
        with engine.begin() as connection:
            run(connection)
    finally:
        engine.dispose()
