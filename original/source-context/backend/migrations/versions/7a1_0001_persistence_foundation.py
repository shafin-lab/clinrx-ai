"""Initial patient/encounter/fact envelopes; synthetic local development only.

DDL is intentionally explicit and independent of future ORM definitions.
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = '7a1_0001'
down_revision = None
branch_labels = None
depends_on = None


def envelope_columns():
    return [sa.Column('payload_version', sa.Integer(), nullable=False),
            sa.Column('payload', sa.Text(), nullable=False),
            sa.Column('ingested_at', sa.Text(), nullable=False)]


def upgrade():
    identity = op.create_table('repository_identity',
        sa.Column('singleton', sa.Integer(), primary_key=True),
        sa.Column('repository_id', sa.Text(), nullable=False, unique=True),
        sa.CheckConstraint('singleton = 1', name='ck_repository_singleton'))
    op.bulk_insert(identity, [{'singleton': 1, 'repository_id': str(uuid4())}])
    op.create_table('patient',
        sa.Column('patient_id', sa.Text(), primary_key=True),
        *envelope_columns(),
        sa.CheckConstraint('payload_version = 1', name='ck_patient_payload_version'))
    op.create_table('encounter',
        sa.Column('encounter_id', sa.Text(), primary_key=True),
        sa.Column('patient_id', sa.Text(), sa.ForeignKey('patient.patient_id'), nullable=False),
        *envelope_columns(),
        sa.UniqueConstraint('encounter_id', 'patient_id', name='uq_encounter_owner'),
        sa.CheckConstraint('payload_version = 1', name='ck_encounter_payload_version'))
    op.create_table('fact_revision',
        sa.Column('ingestion_sequence', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('fact_id', sa.Text(), nullable=False),
        sa.Column('revision', sa.Text(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('encounter_id', sa.Text(), nullable=False),
        *envelope_columns(),
        sa.UniqueConstraint('kind', 'fact_id', 'revision', name='uq_fact_exact_revision'),
        sa.ForeignKeyConstraint(['encounter_id', 'patient_id'],
                                ['encounter.encounter_id', 'encounter.patient_id'],
                                name='fk_fact_encounter_owner'),
        sa.CheckConstraint("kind IN ('observation', 'medication_order', 'medication_administration', 'inference')",
                           name='ck_fact_supported_kind'),
        sa.CheckConstraint('payload_version = 1', name='ck_fact_payload_version'),
        sqlite_autoincrement=True)


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
