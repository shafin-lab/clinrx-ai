import {key, pin, stable, type Catalog, type Evidence} from '../api/rf2Client';
import type {SavedReview} from '../clinical/savedReviewStore';
import {compareLaboratoryCollections, laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryQualifications, laboratoryResultText} from '../gastrointestinal/laboratoryPresentation';
import {compareRespiratoryInstants as compareInstants} from '../respiratory/exactTime';
import {asObject} from '../respiratory/respiratoryModel';

export interface NeurologicalScope {
  patient: string;
  encounter: string;
  start: string;
  end: string;
}

const laboratoryLabels: Record<string, string> = {
  sodium: 'Sodium', glucose: 'Glucose', potassium: 'Potassium',
  total_calcium: 'Total calcium', ionised_calcium: 'Ionised calcium',
  magnesium: 'Magnesium', creatinine: 'Creatinine', urea: 'Urea',
  bun: 'Blood urea nitrogen', ammonia: 'Ammonia',
};
const contentStatuses = new Set(['preliminary', 'interim', 'final', 'corrected']);
export const text = (value: unknown) => typeof value === 'string' ? value : '';
export const sourceStatus = (source: Evidence) =>
  [text(source.fact.report_status), text(source.fact.record_status)].filter(Boolean).join(' · ');
export const hasRecordedContent = (source: Evidence) =>
  !source.superseded && source.fact.record_status === 'recorded' && contentStatuses.has(text(source.fact.report_status));
export const sourceNarrative = (source: Evidence) =>
  hasRecordedContent(source) ? text(source.fact.narrative) : sourceStatus(source);

function instant(value: unknown) {
  return typeof value === 'string' && compareInstants(value, value) === 0 ? value : null;
}

function timedField(source: Evidence, field: string) {
  return asObject(asObject(source.fact.times)[field]);
}

export function occurredAt(source: Evidence) {
  if (source.fact.kind === 'medication_administration') return instant(source.fact.administered_at);
  const at = timedField(source, 'occurred');
  return at.status === 'known' && at.precision === 'instant' ? instant(at.value) : null;
}

export function sourceTime(source: Evidence, field = 'occurred') {
  if (source.fact.kind === 'medication_administration') return occurredAt(source) ?? 'Administration time unknown';
  const at = timedField(source, field);
  if (at.status === 'known') {
    if (at.precision === 'instant') return instant(at.value) ?? 'Time unknown';
    if (at.precision === 'bounded') return [at.lower, at.upper].filter(Boolean).join(' → ');
    if (at.precision === 'approximate') return 'Approximately ' + text(at.value);
    if (at.precision === 'day') return text(at.value).slice(0, 10);
  }
  return at.status === 'unknown' ? 'Time unknown' : 'Time not recorded';
}

function scopeMatches(catalog: Catalog, requested: NeurologicalScope) {
  const scope = catalog.combined.context.scope;
  return catalog.execution_enabled === false && catalog.combined.execution_enabled === false &&
    catalog.repository === catalog.cutoff.repository_id && scope.repository_cutoff.repository_id === catalog.repository &&
    scope.repository_cutoff.fact_watermark === catalog.cutoff.fact_watermark &&
    scope.patient_id === requested.patient && scope.encounter_id === requested.encounter &&
    compareInstants(scope.review_start, requested.start) === 0 && compareInstants(scope.review_end, requested.end) === 0;
}

function inScope(source: Evidence, catalog: Catalog, requested: NeurologicalScope) {
  const target = source.fact.binding.target;
  return source.repository === catalog.repository && source.ingestion.repository_id === catalog.repository &&
    source.ingestion.ingestion_sequence <= source.cutoff && source.cutoff <= catalog.cutoff.fact_watermark &&
    target.patient_id === requested.patient && target.encounter_id === requested.encounter;
}

function withinPeriod(source: Evidence, {start, end}: NeurologicalScope) {
  if (source.fact.kind === 'medication_administration') {
    const at = occurredAt(source);
    const recordedAt = instant(asObject(source.fact.time).recorded);
    return !!at && compareInstants(at, start) !== -1 && compareInstants(at, end) !== 1 &&
      (!recordedAt || compareInstants(recordedAt, end) !== 1);
  }
  const field = source.fact.kind === 'laboratory_report' ? 'collected' : 'occurred';
  const primary = timedField(source, field);
  const upper = primary.status === 'known' && primary.precision !== 'day' ? instant(primary.upper ?? primary.value) : null;
  if (upper && compareInstants(upper, start) === -1) return false;
  return [field, 'reported', 'available'].every(name => {
    const time = timedField(source, name);
    const latest = time.status === 'known' && time.precision !== 'day' ? instant(time.upper ?? time.value) : null;
    return !latest || compareInstants(latest, end) !== 1;
  });
}

function labRows(sources: Evidence[]) {
  return sources.flatMap(source => {
    const collection = laboratoryCollection(source.fact);
    const components = Array.isArray(source.fact.components) ? source.fact.components : [];
    return components.flatMap(raw => {
      const component = asObject(raw);
      const concept = text(component.mapped_concept);
      if (component.mapping_status !== 'mapped' || !Object.hasOwn(laboratoryLabels, concept)) return [];
      return [{
        source, collection, label: laboratoryLabels[concept], component: text(component.source_component_id),
        value: hasRecordedContent(source) ? laboratoryResultText(component) : sourceStatus(source),
        qualifications: laboratoryQualifications(source, component),
      }];
    });
  }).sort((a, b) => compareLaboratoryCollections(a.collection.instant, b.collection.instant));
}

export function medicationName(source: Evidence) {
  return text(asObject(source.fact.medication).name);
}

export function administrationText(source: Evidence) {
  const medication = asObject(source.fact.medication);
  const ingredients = Array.isArray(medication.ingredient_ids) ? medication.ingredient_ids.join(', ') : '';
  const dose = asObject(asObject(source.fact.administered_dose).amount);
  const value = typeof dose.value === 'number' ? String(dose.value) : text(dose.value);
  return [
    [ingredients, text(medication.product_id), text(medication.formulation)].filter(Boolean).join(' · '),
    [value, text(asObject(dose.unit).raw)].filter(Boolean).join(' '), text(source.fact.route),
  ].filter(Boolean).join(' · ');
}

export function medicationsByExam(sources: Evidence[], examTime: string | null) {
  if (!examTime) return [];
  const groups = new Map<string, Evidence[]>();
  for (const source of sources) {
    const at = occurredAt(source);
    const name = medicationName(source).trim().toLowerCase();
    if (!name || !at || compareInstants(at, examTime) === 1) continue;
    const existing = groups.get(name);
    if (!existing) groups.set(name, [source]);
    else if (compareInstants(at, occurredAt(existing[0])!) === 0) existing.push(source);
  }
  return [...groups.values()].flat();
}

function pinIdentity(pins: unknown[]) {
  return stable(pins.map(value => {
    const {cutoff: _cutoff, ...identity} = asObject(value);
    return stable(identity);
  }).sort());
}

export function neurologicalModel(catalog: Catalog | undefined, requested: NeurologicalScope) {
  const valid = !!catalog && scopeMatches(catalog, requested);
  const filtered = (sources: Evidence[]) => valid
    ? sources.filter(source => inScope(source, catalog, requested) && withinPeriod(source, requested))
    : [];
  const records = filtered(catalog?.neurological_records ?? []).filter(source => source.fact.kind === 'neurological_record')
    .sort((a, b) => compareLaboratoryCollections(occurredAt(a), occurredAt(b)));
  const exams = records.filter(source => source.fact.category === 'exam');
  const imaging = records.filter(source => source.fact.category === 'imaging');
  const medications = records.filter(source => source.fact.category === 'medication_status');
  const labs = labRows(filtered(catalog?.laboratory_reports ?? []));
  const administrations = filtered(catalog?.medication_administrations ?? [])
    .filter(source => source.fact.kind === 'medication_administration')
    .sort((a, b) => compareLaboratoryCollections(occurredAt(a), occurredAt(b)));
  const latestTime = exams[0] ? occurredAt(exams[0]) : null;
  const latest = latestTime && hasRecordedContent(exams[0]) && exams[0].fact.conflict !== 'unresolved' &&
    exams.slice(1).every(source => {
      const at = occurredAt(source);
      return !!at && compareInstants(latestTime, at) === 1;
    }) ? exams[0] : undefined;
  const sources = [...new Map([...records, ...labs.map(row => row.source), ...administrations]
    .map(source => [key(pin(source)), source])).values()];
  const pins = sources.map(source => ({
    repository: source.repository, kind: source.fact.kind, id: source.fact.id, version: source.fact.revision,
    digest: source.digest, ingestion: source.ingestion.ingestion_sequence, cutoff: source.cutoff,
  }));
  const signature = valid ? stable(['m13/v1', requested.patient, requested.encounter, requested.start, requested.end,
    catalog.repository, catalog.neurological_records !== undefined, catalog.medication_administrations !== undefined]) : '';
  const identity = stable([signature, pinIdentity(pins)]);

  function matches(review: SavedReview<unknown>) {
    const cutoff = asObject(review.snapshot.cutoff);
    return valid && review.domain === 'M13' && review.patient === requested.patient && review.encounter === requested.encounter &&
      review.repository === catalog.repository && compareInstants(review.period.start, requested.start) === 0 &&
      compareInstants(review.period.end, requested.end) === 0 && review.snapshot.signature === signature &&
      cutoff.repository_id === catalog.repository && Number.isSafeInteger(cutoff.fact_watermark) &&
      Number(cutoff.fact_watermark) <= catalog.cutoff.fact_watermark && review.snapshot.pins.every(value => {
        const stored = asObject(value);
        return stored.repository === catalog.repository && Number(stored.cutoff) >= Number(stored.ingestion) &&
          Number(stored.cutoff) <= Number(cutoff.fact_watermark);
      }) && pinIdentity(review.snapshot.pins) === pinIdentity(pins);
  }

  return {valid, latest, exams, imaging, medications, labs, administrations, sources, pins, signature, identity, matches};
}
