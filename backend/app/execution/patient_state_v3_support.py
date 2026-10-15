"""M7 timing-only consumed provenance; shared by admission and pure selection.

This is capability-specific traversal, not a generic dependency framework.
Assembly bounds its graph; selection permits at most 35 explicit exact pins.
"""
from app.models.clinical import hemodynamics as h
from app.models.clinical.common import Provenance
from app.models.clinical.recorded_v2 import ref_key


def consumed_binding_roles(fact):
    if isinstance(fact,h.PressureObservation):
        return ('device','calibration','zeroing') if fact.acquisition.method=='invasive_arterial' else ('device',)
    if isinstance(fact,h.LactateResult): return ('specimen',)
    if isinstance(fact,h.VasoactiveEvent): return ('delivery',)
    if isinstance(fact,h.MonitoringEvent):
        return ('device',fact.event_type) if fact.event_type in ('calibration','zeroing') else ('device',)
    return ()


def consumed_provenance_references(fact):
    refs = set()
    def visit(value):
        if isinstance(value, Provenance):
            refs.update(value.dependencies)
        if hasattr(type(value),'model_fields'):
            for name in type(value).model_fields:
                visit(getattr(value,name))
        elif isinstance(value,(tuple,list)):
            for child in value: visit(child)
    for binding in fact.associations:
        if binding.role in consumed_binding_roles(fact):
            visit(binding.provenance)
    # These assertions participate in eligibility. Unrelated event context does not.
    visit(fact.provenance)
    if not isinstance(fact,h.LactateResult): visit(fact.occurred)
    if isinstance(fact,h.PressureObservation):
        visit(fact.acquisition.quality.provenance)
        if fact.acquisition.method=='invasive_arterial':
            visit(fact.acquisition.calibration_provenance);visit(fact.acquisition.zeroing_provenance)
        if fact.acquisition.device is not None: visit(fact.acquisition.support_provenance)
    if isinstance(fact,h.MonitoringEvent) and fact.event_type in ('calibration','zeroing'):
        visit(getattr(fact.acquisition,fact.event_type+'_provenance'))
    if isinstance(fact,h.LactateResult):
        visit(fact.collected);visit(fact.collection_assertion);visit(fact.acquisition.quality.provenance)
    if isinstance(fact,h.VasoactiveEvent) and isinstance(fact.action,h.InfusionEvent):
        visit(fact.drug.mapping_provenance);visit(fact.action.delivery.attestation)
    return tuple(sorted(refs, key=ref_key))

