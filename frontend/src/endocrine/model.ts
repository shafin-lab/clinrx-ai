import {key, pin, stable, type Catalog, type Evidence} from '../api/rf2Client';
import type {SavedReview} from '../clinical/savedReviewStore';
import {compareLaboratoryCollections, hasUniqueLatestCollection, laboratoryCollection} from '../clinicalEvidence/laboratoryDisplay';
import {laboratoryQualifications, laboratoryResultText} from '../gastrointestinal/laboratoryPresentation';
import {hasRecordedContent, occurredAt, sourceStatus, sourceTime, text} from '../neurological/model';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {asObject} from '../respiratory/respiratoryModel';

export interface EndocrineScope {
  patient: string;
  encounter: string;
  start: string;
  end: string;
}

type EndocrineCatalog = Catalog & {
  endocrine_records?: Evidence[];
  medication_orders?: Evidence[];
};

const labs: Record<string, [string, string]> = {
  glucose: ['Glucose', 'Glucose'],
  hba1c: ['Diabetes background', 'HbA1c'],
  beta_hydroxybutyrate: ['Ketones and acid–base', 'β-hydroxybutyrate'],
  ph: ['Ketones and acid–base', 'pH'],
  blood_ph: ['Ketones and acid–base', 'pH'],
  urine_ketones: ['Ketones and acid–base', 'Urine ketones'],
  tsh: ['Thyroid', 'TSH'],
  free_t4: ['Thyroid', 'Free T4'],
  cortisol: ['Adrenal and pituitary', 'Cortisol'],
  sodium: ['Adrenal and pituitary', 'Sodium'],
  serum_osmolality: ['Adrenal and pituitary', 'Serum osmolality'],
  urine_osmolality: ['Adrenal and pituitary', 'Urine osmolality'],
  total_calcium: ['Calcium and phosphate', 'Total calcium'],
  ionised_calcium: ['Calcium and phosphate', 'Ionised calcium'],
  phosphate: ['Calcium and phosphate', 'Phosphate'],
  magnesium: ['Calcium and phosphate', 'Magnesium'],
  pth: ['Calcium and phosphate', 'PTH'],
};

const nutritionStates = new Set(['running', 'paused', 'resumed', 'stopped', 'unknown']);
const insulinStates = new Set(['held', 'missed', 'not_given']);
const usable = (evidence: Evidence) => hasRecordedContent(evidence) && evidence.fact.conflict !== 'unresolved' &&
  (evidence.fact.report_status === 'final' || evidence.fact.report_status === 'corrected');
const validInstant = (value: unknown) => typeof value === 'string' && compare(value, value) === 0 ? value : null;

export function endocrineEventTime(source: Evidence) {
  return source.fact.kind === 'medication_order'
    ? validInstant(asObject(source.fact.time).event)
    : occurredAt(source);
}

function inWindow(source: Evidence, {start, end}: EndocrineScope) {
  const fact = source.fact;
  if (fact.kind === 'medication_administration' || fact.kind === 'medication_order') {
    const when = endocrineEventTime(source);
    const recorded = validInstant(asObject(fact.time).recorded);
    const provenance = validInstant(asObject(fact.provenance).recorded_at);
    return !!when && compare(when, start) !== -1 && compare(when, end) !== 1 &&
      [recorded, provenance].every(at => !at || compare(at, end) !== 1);
  }
  const primary = fact.kind === 'laboratory_report' ? 'collected' : 'occurred';
  const timestamps = asObject(fact.times);
  const upper = (name: string) => {
    const at = asObject(timestamps[name]);
    return at.status === 'known' && at.precision !== 'day' ? validInstant(at.upper ?? at.value) : null;
  };
  const occurred = upper(primary);
  return (!occurred || compare(occurred, start) !== -1) &&
    [primary, 'reported', 'available'].every(name => {
      const at = upper(name);
      return !at || compare(at, end) !== 1;
    });
}

function toLabRows(source: Evidence) {
  const collection = laboratoryCollection(source.fact);
  const specimen = asObject(asObject(source.fact.specimen).specimen_type);
  const specimenLabel = text(specimen.raw_display) || 'Specimen not recorded';
  const specimenKey = [text(specimen.namespace), text(specimen.code), text(specimen.raw_display)].join('|').toLowerCase();
  const components = Array.isArray(source.fact.components) ? source.fact.components : [];
  return components.flatMap(raw => {
    const component = asObject(raw);
    const concept = text(component.mapped_concept);
    if (component.mapping_status !== 'mapped' || !Object.hasOwn(labs, concept)) return [];
    const [group, label] = labs[concept];
    const result = asObject(component.result);
    const numeric = usable(source) && result.kind === 'numeric' && result.comparator === '=' ? text(result.raw_value) : '';
    const unit = text(asObject(result.unit).raw_display);
    const qualifications = laboratoryQualifications(source, component, false);
    const reportStatus = text(source.fact.report_status);
    const statusLabel = source.fact.record_status === 'withdrawn' || reportStatus === 'withdrawn'
      ? 'Withdrawn source result'
      : reportStatus === 'corrected' ? 'Corrected source result'
        : reportStatus && reportStatus !== 'final' ? reportStatus[0].toUpperCase() + reportStatus.slice(1) + ' source result' : '';
    const value = hasRecordedContent(source) ? laboratoryResultText(component) : statusLabel || sourceStatus(source) || 'Result unavailable';
    return [{
      kind: 'lab' as const, source, id: key(pin(source)) + '/' + text(component.source_component_id),
      group, label, concept, specimenLabel, specimenKey, numeric, unit, qualifications, statusLabel, value,
      at: collection.instant, time: collection.text,
    }];
  });
}

export type LabRow = ReturnType<typeof toLabRows>[number];

function medicationName(source: Evidence) {
  const medication = asObject(source.fact.medication);
  const ingredients = Array.isArray(medication.ingredient_ids) ? medication.ingredient_ids : [];
  const isInsulin = (value: unknown): value is string => typeof value === 'string' && /^insulin(?:\b|_)/i.test(value.trim());
  const matched = ingredients.filter(isInsulin);
  return matched.length ? matched.join(' · ') : isInsulin(medication.product_id) ? medication.product_id : '';
}

function doseText(raw: unknown) {
  const amount = asObject(asObject(raw).amount);
  const value = typeof amount.value === 'number' ? String(amount.value) : text(amount.value);
  return [value, text(asObject(amount.unit).raw)].filter(Boolean).join(' ');
}

const eventLabels: Record<string, string> = {given: 'Given', ordered: 'Ordered', held: 'Held', missed: 'Missed', not_given: 'Not given'};

export function endocrineEvent(source: Evidence) {
  const fact = source.fact;
  const at = endocrineEventTime(source);
  const base = {kind: 'event' as const, source, id: key(pin(source)), at,
    time: at ?? (fact.kind === 'medication_order' ? 'Order time not recorded' : sourceTime(source)),
  };
  if (fact.kind === 'endocrine_record') {
    if (fact.category === 'nutrition') {
      const nutrition = asObject(fact.nutrition);
      const name = [text(nutrition.route), 'feed'].filter(Boolean).join(' ');
      const status = text(nutrition.status);
      const current = usable(source) && nutritionStates.has(status);
      return {...base, group: 'nutrition' as const, status: current ? status : '', label: name,
        detail: current ? status : sourceStatus(source) || 'Status unavailable'};
    }
    if (fact.category === 'insulin_non_delivery') {
      const insulin = asObject(fact.insulin);
      const status = text(insulin.status);
      const current = usable(source) && insulinStates.has(status);
      return {...base, group: 'insulin' as const, status: current ? status : '', label: text(insulin.name) || 'Insulin',
        detail: current ? text(insulin.reason) : sourceStatus(source) || 'Status unavailable'};
    }
    return null;
  }
  const name = medicationName(source);
  if (!name) return null;
  const given = fact.kind === 'medication_administration';
  return {...base, group: 'insulin' as const,
    status: fact.conflict === 'unresolved' || source.superseded ? '' : given ? 'given' : 'ordered',
    label: name,
    detail: [doseText(given ? fact.administered_dose : fact.prescribed_dose), text(fact.route),
      ...(given ? [] : [text(fact.order_status), text(fact.schedule_text)])].filter(Boolean).join(' · '),
  };
}

export type EventRow = NonNullable<ReturnType<typeof endocrineEvent>>;
export const displayEvent = (row: EventRow) => row.group === 'nutrition'
  ? [row.label, row.detail].filter(Boolean).join(' · ')
  : [eventLabels[row.status] || 'Status unconfirmed', row.label, row.detail].filter(Boolean).join(' · ');

function sameScope(catalog: Catalog, requested: EndocrineScope) {
  const scope = catalog.combined.context.scope;
  return catalog.execution_enabled === false && catalog.combined.execution_enabled === false &&
    catalog.repository === catalog.cutoff.repository_id && scope.repository_cutoff.repository_id === catalog.repository &&
    scope.repository_cutoff.fact_watermark === catalog.cutoff.fact_watermark &&
    scope.patient_id === requested.patient && scope.encounter_id === requested.encounter &&
    compare(scope.review_start, requested.start) === 0 && compare(scope.review_end, requested.end) === 0;
}

function samePatient(source: Evidence, catalog: Catalog, requested: EndocrineScope) {
  const target = source.fact.binding.target;
  return source.repository === catalog.repository && source.ingestion.repository_id === catalog.repository &&
    source.ingestion.ingestion_sequence <= source.cutoff && source.cutoff <= catalog.cutoff.fact_watermark &&
    target.patient_id === requested.patient && target.encounter_id === requested.encounter;
}

function pinIdentity(pins: unknown[]) {
  return stable(pins.map(value => {
    const {cutoff: _cutoff, ...identity} = asObject(value);
    return stable(identity);
  }).sort());
}

export function endocrineModel(catalog: EndocrineCatalog | undefined, requested: EndocrineScope) {
  const valid = !!catalog && sameScope(catalog, requested);
  const bounded = (evidence: Evidence[]) => valid
    ? evidence.filter(source => samePatient(source, catalog, requested) && inWindow(source, requested))
    : [];
  const labRows = bounded(catalog?.laboratory_reports ?? []).flatMap(toLabRows)
    .sort((a, b) => compareLaboratoryCollections(a.at, b.at));
  const glucose = labRows.filter(row => row.concept === 'glucose');
  const latest = hasUniqueLatestCollection(glucose.map(row => row.at)) && glucose[0].numeric && glucose[0].unit
    ? glucose[0] : undefined;
  const comparable = latest && latest.specimenLabel !== 'Specimen not recorded'
    ? glucose.filter(row => row.at && row.numeric && row.unit === latest.unit && row.specimenKey === latest.specimenKey)
    : [];
  const trend = comparable.length > 1 && comparable.every((row, index) => index === 0 || compare(comparable[index - 1].at!, row.at!) === 1)
    ? [...comparable.slice(0, 3)].reverse().map(row => row.numeric).join(' → ') + ' ' + latest?.unit
    : '';

  const events = bounded([
    ...(catalog?.endocrine_records ?? []), ...(catalog?.medication_administrations ?? []), ...(catalog?.medication_orders ?? []),
  ]).flatMap(source => endocrineEvent(source) ?? []).sort((a, b) => compareLaboratoryCollections(a.at, b.at));
  const timeline = [...glucose, ...events].sort((a, b) => {
    if (a.at && b.at) return compare(a.at, b.at) ?? 0;
    return a.at ? -1 : b.at ? 1 : 0;
  });
  const sources = [...new Map([...labRows, ...events].map(row => [key(pin(row.source)), row.source])).values()];
  const pins = sources.map(source => ({
    repository: source.repository, kind: source.fact.kind, id: source.fact.id, version: source.fact.revision,
    digest: source.digest, ingestion: source.ingestion.ingestion_sequence, cutoff: source.cutoff,
  }));
  const signature = valid ? stable(['m14/v1', requested.patient, requested.encounter, requested.start, requested.end,
    catalog.repository, catalog.endocrine_records !== undefined, catalog.medication_administrations !== undefined,
    catalog.medication_orders !== undefined]) : '';
  const identity = stable([signature, pinIdentity(pins)]);
  const matches = (review: SavedReview<unknown>) => {
    const cutoff = asObject(review.snapshot.cutoff);
    return valid && review.domain === 'M14' && review.patient === requested.patient && review.encounter === requested.encounter &&
      review.repository === catalog.repository && review.snapshot.signature === signature &&
      compare(review.period.start, requested.start) === 0 && compare(review.period.end, requested.end) === 0 &&
      cutoff.repository_id === catalog.repository && Number.isSafeInteger(cutoff.fact_watermark) &&
      Number(cutoff.fact_watermark) <= catalog.cutoff.fact_watermark && review.snapshot.pins.every(value => {
        const stored = asObject(value);
        return stored.repository === catalog.repository && Number(stored.cutoff) >= Number(stored.ingestion) &&
          Number(stored.cutoff) <= Number(cutoff.fact_watermark);
      }) && pinIdentity(review.snapshot.pins) === pinIdentity(pins);
  };

  function latestEvent(relevant: EventRow[]) {
    return hasUniqueLatestCollection(relevant.map(event => event.at)) && relevant[0].status ? relevant[0] : undefined;
  }

  const insulinEvents = events.filter(event => event.group === 'insulin' && event.source.fact.kind !== 'medication_order');
  const latestInsulin = latestEvent(insulinEvents);
  const lastGiven = latestEvent(insulinEvents.filter(event => event.status === 'given'));
  const latestFeed = latestEvent(events.filter(event => event.group === 'nutrition'));
  return {valid, latest, trend, latestInsulin, lastGiven, latestFeed, timeline,
    otherLabs: labRows.filter(row => row.concept !== 'glucose'), sources, pins, signature, identity, matches};
}

export type EndocrineModel = ReturnType<typeof endocrineModel>;
