"""Add immutable revision links without rewriting any 7A.1 record.

Legacy preflight is deliberately local to this migration, not current ORM code.
"""
import json
from datetime import datetime
from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision = '7a2_0002'
down_revision = '7a1_0001'
branch_labels = None
depends_on = None


def _preflight(connection):
    try:
        identities = connection.execute(sa.text('SELECT singleton, repository_id FROM repository_identity')).all()
        if len(identities) != 1 or identities[0][0] != 1:
            raise ValueError()
        UUID(identities[0][1])
        if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
            raise ValueError()
        seen = set()
        for row in connection.execute(sa.text('SELECT * FROM fact_revision')).mappings():
            identity = (row['kind'], row['fact_id'])
            payload = json.loads(row['payload'])
            if identity in seen or row['payload_version'] != 1 or row['ingestion_sequence'] <= 0:
                raise ValueError()
            seen.add(identity)
            if (payload['kind'], payload['id'], payload['revision']) != (*identity, row['revision']):
                raise ValueError()
            if payload.get('supersedes') is not None or payload.get('correction_reason') is not None:
                raise ValueError()
            target = payload['binding']['target']
            if (target['patient_id'], target['encounter_id'], target.get('longitudinal_context_id')) != (
                    row['patient_id'], row['encounter_id'], None):
                raise ValueError()
            canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
            if canonical != row['payload'] or datetime.fromisoformat(row['ingested_at']).utcoffset() is None:
                raise ValueError()
        maximum = connection.execute(sa.text('SELECT COALESCE(MAX(ingestion_sequence), 0) FROM fact_revision')).scalar_one()
        sequence = connection.execute(sa.text("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'")).scalar_one_or_none()
        if maximum and (sequence is None or sequence < maximum):
            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError):
        raise RuntimeError('legacy store violates revision-chain migration assumptions') from None


def upgrade():
    _preflight(op.get_bind())
    op.create_table('revision_link',
        sa.Column('successor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), primary_key=True),
        sa.Column('predecessor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), nullable=False, unique=True),
        sa.CheckConstraint('predecessor_sequence < successor_sequence', name='ck_revision_forward'))


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
