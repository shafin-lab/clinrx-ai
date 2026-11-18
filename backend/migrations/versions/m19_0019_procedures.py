"""Admit exact procedure revisions in the shared device history."""
from alembic import op

revision = 'm19_0019'
down_revision = 'm19_0018'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('device_history', recreate='always') as batch:
        batch.drop_constraint('ck_device_history_kind', type_='check')
        batch.create_check_constraint(
            'ck_device_history_kind', "kind IN ('device_episode', 'observation', 'procedure_record')"
        )


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; restore a preserved copy')
