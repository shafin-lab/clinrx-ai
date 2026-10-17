"""SQLite-specific connection policy stays inside this adapter."""
from pathlib import Path

from sqlalchemy import Engine, URL, create_engine, event, text
from sqlalchemy.engine import make_url

from .entities import SCHEMA_REVISION
from .errors import SchemaMismatch, UnsupportedOperation


def create_database(path: str | Path) -> Engine:
    """Open a file database; never implicitly create its schema."""
    return create_sqlite_engine(URL.create('sqlite+pysqlite', database=str(Path(path).resolve())))


def create_sqlite_engine(url: str | URL) -> Engine:
    url = make_url(url)
    if url.drivername != 'sqlite+pysqlite' or not url.database or url.database == ':memory:' or url.query:
        raise UnsupportedOperation('only ordinary file-backed SQLite URLs are supported')
    engine = create_engine(url, connect_args={'timeout': 5}, hide_parameters=True)

    @event.listens_for(engine, 'connect')
    def configure(connection, _record):
        # Disable sqlite3 legacy transaction handling, including its DDL behavior.
        connection.isolation_level = None
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA synchronous=FULL')
        if cursor.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
            raise RuntimeError('SQLite foreign-key enforcement is required')
        cursor.close()

    @event.listens_for(engine, 'begin')
    def begin(connection):
        # Local slice: serialize repository transactions, including read/check/write.
        # This also makes a captured ingestion sequence a stable committed prefix.
        connection.exec_driver_sql('BEGIN IMMEDIATE')

    return engine


def require_schema(connection) -> None:
    from sqlalchemy.exc import OperationalError

    try:
        revisions = connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    except OperationalError as exc:
        raise SchemaMismatch('database requires the reviewed Alembic migration') from exc
    if revisions != [SCHEMA_REVISION]:
        raise SchemaMismatch('unsupported database schema revision')
