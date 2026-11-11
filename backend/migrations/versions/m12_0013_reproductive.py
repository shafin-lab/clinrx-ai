"""Admit reproductive source revisions while preserving all existing rows and sequence watermarks."""
from alembic import op
import sqlalchemy as sa

revision = 'm12_0013'
down_revision = 'm11_0012'
branch_labels = None
depends_on = None


KINDS = "'observation', 'medication_order', 'medication_administration', 'inference', 'microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture', 'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance', 'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle', 'antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery', 'circulatory_pressure', 'circulatory_cardiac', 'circulatory_volume', 'circulatory_dynamic', 'circulatory_device_prediction', 'circulatory_perfusion', 'circulatory_oxygen', 'circulatory_lactate', 'circulatory_echo', 'circulatory_ecg', 'circulatory_vasoactive', 'circulatory_monitoring', 'circulatory_assessment', 'circulatory_event', 'circulatory_signal', 'laboratory_report', 'respiratory_record', 'gastrointestinal_record', 'reproductive_record', 'transfusion_administration', 'haemostatic_medication_course', 'transfusion_request', 'transfusion_prescription', 'blood_product_disposition', 'transfusion_compatibility', 'transfusion_reaction', 'haemorrhage_episode', 'm10_assessment', 'transfusion_coverage_link', 'fluid_administration_link', 'm10_medication_detail', 'viscoelastic_report'"


def upgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('foreign-key integrity required before M12 migration')
    sequence = connection.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name='fact_revision'").scalar_one_or_none()
    connection.exec_driver_sql('CREATE TEMP TABLE m12_revision_links AS SELECT * FROM revision_link')
    op.drop_table('revision_link')
    with op.batch_alter_table('fact_revision', recreate='always', table_kwargs={'sqlite_autoincrement': True}) as batch:
        batch.drop_constraint('ck_fact_supported_kind', type_='check')
        batch.create_check_constraint('ck_fact_supported_kind', f'kind IN ({KINDS})')
    connection.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='fact_revision'")
    if sequence is not None:
        connection.execute(sa.text("INSERT INTO sqlite_sequence (name, seq) VALUES ('fact_revision', :sequence)"),
                           {'sequence': sequence})
    op.create_table('revision_link',
        sa.Column('successor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), primary_key=True),
        sa.Column('predecessor_sequence', sa.Integer(), sa.ForeignKey('fact_revision.ingestion_sequence'), nullable=False, unique=True),
        sa.CheckConstraint('predecessor_sequence < successor_sequence', name='ck_revision_forward'))
    connection.exec_driver_sql('INSERT INTO revision_link SELECT * FROM m12_revision_links')
    connection.exec_driver_sql('DROP TABLE m12_revision_links')
    if connection.exec_driver_sql('PRAGMA foreign_key_check').first():
        raise RuntimeError('M12 migration failed foreign-key verification')


def downgrade():
    raise RuntimeError('destructive downgrade is not supported; restore a preserved copy')
