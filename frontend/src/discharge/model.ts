import {useEffect, useState} from 'react';
import {hash, key, pin, stable, type Catalog, type Evidence} from '../api/rf2Client';
import type {AntibioticBundle} from '../api/antibioticClient';
import {microReference} from '../antibioticWorkflow/patientModel';
import type {SavedReview} from '../clinical/savedReviewStore';
import type {DeviceState} from '../devices/deviceHistory';
import {reviewPin} from '../nutrition/catalogModel';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {matchesM10Snapshot} from '../transfusion/client';
import type {M10Read} from '../transfusion/types';

export interface Requested {patient: string; encounter: string; start: string; end: string}
export interface Inputs {
  catalog?: Catalog; bundle?: AntibioticBundle; devices: DeviceState; m10: M10Read; requested: Requested;
}
export const transitionLabel = (value: unknown) => value === 'icu_to_ward' ? 'ICU to ward transfer' : 'Home discharge';
export const words = (value: unknown) => typeof value === 'string' ? value.replaceAll('_', ' ') : '';
const sections = ['items', 'laboratory_reports', 'respiratory_records', 'gastrointestinal_records',
  'reproductive_records', 'neurological_records', 'medication_administrations', 'medication_orders',
  'endocrine_records', 'wound_records', 'musculoskeletal_records', 'nutrition_records', 'precaution_records'] as const;

export function dischargeModel({catalog, bundle, devices, m10, requested}: Inputs, selected = '') {
  const scope = catalog?.combined.context.scope;
  const valid = !!catalog && !!scope && catalog.execution_enabled === false && catalog.combined.execution_enabled === false &&
    catalog.repository === catalog.cutoff.repository_id && stable(scope.repository_cutoff) === stable(catalog.cutoff) &&
    scope.patient_id === requested.patient && scope.encounter_id === requested.encounter &&
    compare(scope.review_start, requested.start) === 0 && compare(scope.review_end, requested.end) === 0;
  const bounded = (source: Evidence) => valid && source.repository === catalog.repository &&
    source.ingestion.repository_id === catalog.repository && source.ingestion.ingestion_sequence <= source.cutoff &&
    source.cutoff <= catalog.cutoff.fact_watermark && source.fact.binding.target.patient_id === requested.patient &&
    source.fact.binding.target.encounter_id === requested.encounter;
  const transitions = valid ? (catalog.discharge_records ?? []).filter(bounded) : [];
  const terminal = (source: Evidence) => !source.superseded && source.fact.record_status === 'recorded' &&
    ['final', 'corrected'].includes(String(source.fact.report_status)) && source.fact.conflict !== 'unresolved';
  const plans = [...new Set(transitions.map(source => String(source.fact.transition_id)))];
  const planId = selected || plans[plans.length - 1] || '';
  const records = transitions.filter(source => source.fact.transition_id === planId);
  const active = records.filter(terminal);
  const planTypes = new Set(active.map(source => source.fact.transition));
  const destinations = new Set(active.map(source => source.fact.destination));
  const handover = active.find(source => source.fact.category === 'handover');
  const plan = handover ?? active[0];
  const handoverStates = new Set(active.filter(source => source.fact.category === 'handover').map(source => source.fact.state));
  const handoverConflict = handoverStates.size > 1;
  const planValid = !!plan && planTypes.size === 1 && destinations.size === 1 && !handoverConflict;
  const sources = [...new Map([
    ...(valid ? sections.flatMap(section => catalog[section] ?? []).filter(bounded) : []), ...records,
  ].map(source => [key(pin(source)), source])).values()];
  const microScope = bundle?.micro.assembly.request.scope;
  const microConfirmed = valid && bundle?.renal === catalog && bundle.execution_enabled === false &&
    !!microScope && stable(microScope.repository_cutoff) === stable(catalog.cutoff) &&
    microScope.patient_id === requested.patient && microScope.encounter_id === requested.encounter &&
    compare(microScope.review_start, requested.start) === 0 && compare(microScope.review_end, requested.end) === 0;
  const microItems = microConfirmed ? bundle.micro.assembly.snapshot.items ?? [] : [];
  const devicesConfirmed = devices.status === 'ready' && [...devices.history.episodes, ...devices.history.procedures,
    ...devices.history.outputs].every(item => item.context.patient_id === requested.patient && item.context.encounter_id === requested.encounter);
  const bloodConfirmed = valid && !!m10.snapshot && !m10.loading && !m10.error &&
    matchesM10Snapshot(m10.snapshot, requested, {repository: catalog.repository, cutoff: catalog.cutoff.fact_watermark}, true);
  const blood = bloodConfirmed ? m10.snapshot!.items : [];
  const sourcePins = sources.map(reviewPin);
  const pins = [...sourcePins, ...microItems.map(item => ({reference: microReference(item), expected_digest: item.expected_digest})),
    ...blood.map(item => ({reference: {kind: item.fact.kind, id: item.fact.id, version: item.fact.revision}, expected_digest: item.digest}))];
  const deviceIdentity = devicesConfirmed ? stable(devices.history) : '';
  const signature = stable(['m21/v1', requested, catalog?.repository, planId]);
  const identities = stable([sourcePins.map(p => [p.kind, p.id, p.version, p.digest]).map(stable).sort(),
    microItems.map(item => [microReference(item), item.expected_digest, item.inclusion]).map(stable).sort(),
    blood.map(item => [item.fact.kind, item.fact.id, item.fact.revision, item.digest]).map(stable).sort(), deviceIdentity]);
  // Hashes are fixed length so a long encounter does not exceed the saved-signature bound.
  const complete = valid && planValid && microConfirmed && devicesConfirmed && bloodConfirmed;
  const identity = stable([signature, identities]);
  return {valid, plans, planId, records, active, plan, handover, handoverConflict, planValid, sources, microItems, blood, devicesConfirmed,
    microConfirmed, bloodConfirmed, signature, identities, identity, pins, complete};
}

export function useDischargeModel(inputs: Inputs, selected = '') {
  const model = dischargeModel(inputs, selected);
  const [hashed, setHashed] = useState({identity: '', digest: ''});
  useEffect(() => {
    let current = true;
    void hash(model.identity).then(digest => { if (current) setHashed({identity: model.identity, digest}); }).catch(() => {
      if (current) setHashed({identity: '', digest: ''});
    });
    return () => { current = false; };
  }, [model.identity]);
  const complete = model.complete && hashed.identity === model.identity && !!hashed.digest;
  return {...model, complete, signature: complete ? hashed.digest : '', context: {transitionId: model.planId, deviceHistory: inputs.devices.status === 'ready' ? stable(inputs.devices.history) : ''},
    matches: (review: SavedReview<unknown>) => complete && review.snapshot.signature === hashed.digest &&
      review.snapshot.context?.transitionId === model.planId};
}
