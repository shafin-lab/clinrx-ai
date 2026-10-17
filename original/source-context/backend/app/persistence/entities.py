"""Relational envelopes, not replacement clinical models."""
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_REVISION = 'm7_0008'
PAYLOAD_VERSION = 1


class Base(DeclarativeBase):
    pass


class RepositoryIdentity(Base):
    __tablename__ = 'repository_identity'
    singleton: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[str] = mapped_column(Text, unique=True)
    __table_args__ = (CheckConstraint('singleton = 1', name='ck_repository_singleton'),)


class Envelope:
    payload_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    # UTC ISO text is storage metadata; clinical timestamps remain in the payload.
    ingested_at: Mapped[str] = mapped_column(Text, nullable=False)


class PatientRow(Envelope, Base):
    __tablename__ = 'patient'
    patient_id: Mapped[str] = mapped_column(Text, primary_key=True)
    __table_args__ = (CheckConstraint('payload_version = 1', name='ck_patient_payload_version'),)


class EncounterRow(Envelope, Base):
    __tablename__ = 'encounter'
    encounter_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, ForeignKey('patient.patient_id'), nullable=False)
    __table_args__ = (
        UniqueConstraint('encounter_id', 'patient_id', name='uq_encounter_owner'),
        CheckConstraint('payload_version = 1', name='ck_encounter_payload_version'),
    )


class FactRow(Envelope, Base):
    __tablename__ = 'fact_revision'
    ingestion_sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    fact_id: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[str] = mapped_column(Text, nullable=False)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint('kind', 'fact_id', 'revision', name='uq_fact_exact_revision'),
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
                             ['encounter.encounter_id', 'encounter.patient_id'],
                             name='fk_fact_encounter_owner'),
        CheckConstraint("kind IN ('observation', 'medication_order', 'medication_administration', 'inference', 'microbiology_specimen', 'microbiology_direct_examination', 'microbiology_culture', 'microbiology_isolate', 'microbiology_susceptibility', 'microbiology_resistance', 'microbiology_molecular', 'blood_culture_set', 'blood_culture_bottle', 'antimicrobial_order', 'antimicrobial_administration', 'antimicrobial_non_delivery', 'circulatory_pressure', 'circulatory_cardiac', 'circulatory_volume', 'circulatory_dynamic', 'circulatory_device_prediction', 'circulatory_perfusion', 'circulatory_oxygen', 'circulatory_lactate', 'circulatory_echo', 'circulatory_ecg', 'circulatory_vasoactive', 'circulatory_monitoring', 'circulatory_assessment', 'circulatory_event', 'circulatory_signal')",
                        name='ck_fact_supported_kind'),
        CheckConstraint('payload_version = 1', name='ck_fact_payload_version'),
        {'sqlite_autoincrement': True},
    )


class RevisionLink(Base):
    __tablename__ = 'revision_link'
    successor_sequence: Mapped[int] = mapped_column(
        Integer, ForeignKey('fact_revision.ingestion_sequence'), primary_key=True)
    predecessor_sequence: Mapped[int] = mapped_column(
        Integer, ForeignKey('fact_revision.ingestion_sequence'), nullable=False, unique=True)
    __table_args__ = (
        CheckConstraint('predecessor_sequence < successor_sequence', name='ck_revision_forward'),
    )


class WeightTrendExecutionRow(Envelope, Base):
    __tablename__ = 'weight_trend_execution'
    execution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_execution_encounter_owner'),
        CheckConstraint('payload_version = 1', name='ck_execution_payload_version'),
    )


class CreatinineTrendExecutionRow(Envelope, Base):
    __tablename__ = 'creatinine_trend_execution'
    execution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_creatinine_execution_encounter_owner'),
        CheckConstraint('payload_version = 1', name='ck_creatinine_execution_payload_version'),
    )


class PatientStateTemporalExecutionRow(Envelope, Base):
    __tablename__ = 'patient_state_temporal_execution'
    execution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_patient_state_execution_encounter_owner'),
        CheckConstraint('payload_version = 1', name='ck_patient_state_execution_payload_version'),
    )


class MicroAntimicrobialExecutionRow(Envelope, Base):
    __tablename__ = 'micro_antimicrobial_execution'
    execution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_patient_state_v2_execution_encounter_owner'),
        CheckConstraint('payload_version = 1', name='ck_patient_state_v2_execution_payload_version'),
    )


class CirculatoryExecutionRow(Envelope, Base):
    __tablename__ = 'circulatory_execution'
    execution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['encounter_id', 'patient_id'],
            ['encounter.encounter_id', 'encounter.patient_id'], name='fk_circulatory_execution_owner'),
        CheckConstraint('payload_version = 1', name='ck_circulatory_execution_payload_version'),
    )
