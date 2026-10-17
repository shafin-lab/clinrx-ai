"""One immutable synthetic weight execution envelope; no clinical fact changes."""
from alembic import op
import sqlalchemy as sa

revision = '7b1_0003'
down_revision = '7a2_0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('weight_trend_execution',
        sa.Column('execution_id', sa.Text(), primary_key=True),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('encounter_id', sa.Text(), nullable=False),
        sa.Column('payload_version', sa.Integer(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('payload_digest', sa.Text(), nullable=False),
        sa.Column('ingested_at', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_execution_encounter_owner'),
        sa.CheckConstraint('payload_version = 1', name='ck_execution_payload_version'))


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
