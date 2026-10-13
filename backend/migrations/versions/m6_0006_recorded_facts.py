"""Extend fact kinds atomically, preserving bytes, links and allocator high-water mark."""
from alembic import op
import sqlalchemy as sa

revision = 'm6_0006'
down_revision = 'm4_0005'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('foreign-key integrity required before fact-kind migration')
    sequence = connection.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'").scalar_one_or_none()
    # SQLite requires a table copy to extend CHECK. Remove only the referencing
    # link table after backing it up inside this same transactional DDL boundary.
    connection.exec_driver_sql('CREATE TEMP TABLE m6_revision_links AS SELECT * FROM revision_link')
    op.drop_table('revision_link')
    with op.batch_alter_table('fact_revision', recreate='always', table_kwargs={'sqlite_autoincrement': True}) as batch:
        batch.drop_constraint('ck_fact_supported_kind', type_='check')
        batch.create_check_constraint('ck_fact_supported_kind', "kind IN ('observation', 'medication_order', 'medication_administration', 'inference', 'microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture', 'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance', 'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle', 'antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery')")
    if sequence is None:
        connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='fact_revision'")
    else:
        connection.execute(sa.text("UPDATE sqlite_sequence SET seq=:sequence WHERE name='fact_revision'"), {'sequence': sequence})
    op.create_table('revision_link',
        sa.Column('successor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), primary_key=True),
        sa.Column('predecessor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), nullable=False, unique=True),
        sa.CheckConstraint('predecessor_sequence < successor_sequence', name='ck_revision_forward'))
    connection.exec_driver_sql('INSERT INTO revision_link SELECT * FROM m6_revision_links')
    connection.exec_driver_sql('DROP TABLE m6_revision_links')
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('fact-kind migration failed foreign-key verification')


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
