"""Source-linked device episodes and drain output associations."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .common import ContextTarget, DomainModel, Reference, Source, Text, require_kind
from .recorded_v2 import RawText, RecordedTime, missing_time


class DeviceEpisode(DomainModel):
    """A source revision of one physical device episode."""

    reference: Reference
    context: ContextTarget
    source: Source
    device_type: Text
    site: Text | None = None
    laterality: Text | None = None
    indication: Text | None = None
    status: Literal['in_place', 'removed', 'unknown']
    inserted: RecordedTime = Field(default_factory=missing_time)
    removed: RecordedTime = Field(default_factory=missing_time)
    replaces: Reference | None = None

    @model_validator(mode='after')
    def validate_identity(self):
        require_kind(self.reference, 'device_episode')
        if self.replaces is not None:
            require_kind(self.replaces, 'device_episode')
            if self.replaces.id == self.reference.id:
                raise ValueError('replacement requires a different episode identity')
        return self


class DeviceOutputLink(DomainModel):
    """A recorded association to an existing output, with its asserted target if supplied."""

    output: Reference
    context: ContextTarget
    device: Reference | None = None

    @model_validator(mode='after')
    def validate_references(self):
        require_kind(self.output, 'observation')
        if self.device is not None:
            require_kind(self.device, 'device_episode')
        return self


class ProcedureRecord(DomainModel):
    """One source revision of a planned, performed or cancelled procedure."""

    reference: Reference
    context: ContextTarget
    source: Source
    title: RawText
    status: Literal['planned', 'performed', 'cancelled', 'unknown']
    occurred: RecordedTime = Field(default_factory=missing_time)
    author: RawText | None = None
    method: RawText | None = None
    site: RawText | None = None
    complications: RawText | None = None
    follow_up: RawText | None = None
    devices: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()
    reports: Annotated[tuple[Reference, ...], Field(max_length=32)] = ()

    @model_validator(mode='after')
    def validate_references(self):
        require_kind(self.reference, 'procedure_record')
        for device in self.devices:
            require_kind(device, 'device_episode')
        if not self.title.strip() or len(set(self.devices)) != len(self.devices):
            raise ValueError('procedure requires a title and unique device references')
        if self.reference in self.reports or len(set(self.reports)) != len(self.reports):
            raise ValueError('procedure reports must be unique external references')
        return self


class DeviceHistory(DomainModel):
    """Resolve explicit device references within the supplied evidence."""

    episodes: tuple[DeviceEpisode, ...] = ()
    outputs: tuple[DeviceOutputLink, ...] = ()
    procedures: tuple[ProcedureRecord, ...] = ()

    @model_validator(mode='after')
    def validate_associations(self):
        episodes = {episode.reference: episode for episode in self.episodes}
        if len(episodes) != len(self.episodes):
            raise ValueError('duplicate device revision')
        if len({link.output for link in self.outputs}) != len(self.outputs):
            raise ValueError('duplicate output association')
        if len({record.reference for record in self.procedures}) != len(self.procedures):
            raise ValueError('duplicate procedure revision')
        for procedure in self.procedures:
            for reference in procedure.devices:
                device = episodes.get(reference)
                if device is not None and device.context != procedure.context:
                    raise ValueError('procedure and device context differ')
        for episode in self.episodes:
            predecessor = episodes.get(episode.replaces)
            if predecessor is not None and predecessor.context.patient_id != episode.context.patient_id:
                raise ValueError('replacement crosses patient context')
        for link in self.outputs:
            device = episodes.get(link.device)
            if device is not None and device.context != link.context:
                raise ValueError('output and device context differ')
        return self

    def resolve_output(self, output: Reference) -> DeviceEpisode | None:
        link = next((link for link in self.outputs if link.output == output), None)
        if link is None or link.device is None:
            return None
        return next((episode for episode in self.episodes if episode.reference == link.device), None)



class DeviceHistoryImport(DomainModel):
    repository: UUID
    history: DeviceHistory
