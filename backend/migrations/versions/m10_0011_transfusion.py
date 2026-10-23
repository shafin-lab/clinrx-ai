"""Admit typed transfusion, haemostatic and viscoelastic revisions."""
from alembic import op
import sqlalchemy as sa

revision = 'm10_0011'
down_revision = 'm9_0010'
branch_labels = None
depends_on = None


KINDS = "'observation', 'medication_order', 'medication_administration', 'inference', 'microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture', 'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance', 'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle', 'antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery', 'circulatory_pressure', 'circulatory_cardiac', 'circulatory_volume', 'circulatory_dynamic', 'circulatory_device_prediction', 'circulatory_perfusion', 'circulatory_oxygen', 'circulatory_lactate', 'circulatory_echo', 'circulatory_ecg', 'circulatory_vasoactive', 'circulatory_monitoring', 'circulatory_assessment', 'circulatory_event', 'circulatory_signal', 'laboratory_report', 'respiratory_record', 'transfusion_administration', 'haemostatic_medication_course', 'transfusion_request', 'transfusion_prescription', 'blood_product_disposition', 'transfusion_compatibility', 'transfusion_reaction', 'haemorrhage_episode', 'm10_assessment', 'transfusion_coverage_link', 'fluid_administration_link', 'm10_medication_detail', 'viscoelastic_report'"


def upgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('foreign-key integrity required before M10 migration')
    sequence = connection.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'").scalar_one_or_none()
    connection.exec_driver_sql('CREATE TEMP TABLE m10_revision_links AS SELECT * FROM revision_link')
    op.drop_table('revision_link')
    with op.batch_alter_table('fact_revision', recreate='always', table_kwargs={'sqlite_autoincrement': True}) as batch:
        batch.drop_constraint('ck_fact_supported_kind', type_='check')
        batch.create_check_constraint('ck_fact_supported_kind', f'kind IN ({KINDS})')
    if sequence is None:
        connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='fact_revision'")
    else:
        connection.execute(sa.text("UPDATE sqlite_sequence SET seq=:sequence WHERE name='fact_revision'"), {'sequence': sequence})
    op.create_table('revision_link',
        sa.Column('successor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), primary_key=True),
        sa.Column('predecessor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), nullable=False, unique=True),
        sa.CheckConstraint('predecessor_sequence < successor_sequence', name='ck_revision_forward'))
    connection.exec_driver_sql('INSERT INTO revision_link SELECT * FROM m10_revision_links')
    connection.exec_driver_sql('DROP TABLE m10_revision_links')
    op.create_table('m10_command', sa.Column('command_id', sa.String(36), primary_key=True), sa.Column('payload', sa.Text(), nullable=False), sa.Column('response', sa.Text(), nullable=False))
    op.create_table('m10_attachment', sa.Column('digest', sa.String(64), primary_key=True), sa.Column('media_type', sa.String(128), nullable=False), sa.Column('payload', sa.LargeBinary(), nullable=False))
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('M10 migration failed foreign-key verification')


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; use a new disposable test database')
