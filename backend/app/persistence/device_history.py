"""Persistence mapping for device episode revisions and output associations."""
from pydantic import ValidationError
from sqlalchemy import select

from app.models.clinical.devices import DeviceEpisode, DeviceHistory, DeviceOutputLink, ProcedureRecord

from .canonical import canonical_payload
from .entities import DeviceHistoryRow, PAYLOAD_VERSION
from .errors import StorageIntegrityError


def records(history):
    for episode in history.episodes:
        yield episode.reference, episode
    for link in history.outputs:
        yield link.output, link
    for procedure in history.procedures:
        yield procedure.reference, procedure


def load_history(session, target):
    rows = session.scalars(select(DeviceHistoryRow).where(
        DeviceHistoryRow.encounter_id == target.encounter_id,
        DeviceHistoryRow.patient_id == target.patient_id,
    ).order_by(DeviceHistoryRow.sequence))
    episodes, outputs, procedures = [], [], []
    try:
        for row in rows:
            if row.payload_version != PAYLOAD_VERSION:
                raise StorageIntegrityError('unsupported device history payload version')
            if row.kind == 'device_episode':
                record = DeviceEpisode.model_validate_json(row.payload)
                reference = record.reference
                episodes.append(record)
            elif row.kind == 'procedure_record':
                record = ProcedureRecord.model_validate_json(row.payload)
                reference = record.reference
                procedures.append(record)
            else:
                record = DeviceOutputLink.model_validate_json(row.payload)
                reference = record.output
                outputs.append(record)
            if record.context != target or (reference.kind, reference.id, reference.version) != (
                row.kind, row.record_id, row.revision
            ):
                raise StorageIntegrityError('device history payload disagrees with storage identity')
        return DeviceHistory(episodes=episodes, outputs=outputs, procedures=procedures)
    except ValidationError:
        raise StorageIntegrityError('invalid stored device history') from None


def make_row(reference, record, ingested_at):
    return DeviceHistoryRow(
        patient_id=record.context.patient_id, encounter_id=record.context.encounter_id,
        kind=reference.kind, record_id=reference.id, revision=reference.version,
        payload=canonical_payload(record), payload_version=PAYLOAD_VERSION, ingested_at=ingested_at,
    )
