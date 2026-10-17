"""Add one immutable patient_state execution envelope; retain all existing data."""
from alembic import op
import sqlalchemy as sa

revision = 'm4_0005'
down_revision = '7b2_0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('patient_state_temporal_execution',
        sa.Column('execution_id', sa.Text(), primary_key=True),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('encounter_id', sa.Text(), nullable=False),
        sa.Column('payload_version', sa.Integer(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('payload_digest', sa.Text(), nullable=False),
        sa.Column('ingested_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_patient_state_execution_encounter_owner'),
        sa.CheckConstraint('payload_version = 1', name='ck_patient_state_execution_payload_version'))


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
