"""Store encounter-scoped device episodes and exact output associations."""
from alembic import op
import sqlalchemy as sa

revision = 'm19_0018'
down_revision = 'm16_0017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'device_history',
        sa.Column('sequence', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('encounter_id', sa.Text(), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('record_id', sa.Text(), nullable=False),
        sa.Column('revision', sa.Text(), nullable=False),
        sa.Column('payload_version', sa.Integer(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('ingested_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id', 'patient_id'], ['encounter.encounter_id', 'encounter.patient_id']),
        sa.UniqueConstraint('encounter_id', 'kind', 'record_id', 'revision', name='uq_device_history_exact'),
        sa.CheckConstraint("kind IN ('device_episode', 'observation')", name='ck_device_history_kind'),
        sa.CheckConstraint('payload_version = 1', name='ck_device_history_version'),
    )


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; restore a preserved copy')
