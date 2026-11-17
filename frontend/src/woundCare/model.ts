import {pin, stable, type Catalog, type Evidence} from '../api/rf2Client';
import type {SavedReview} from '../clinical/savedReviewStore';
import {hasRecordedContent, occurredAt, sourceTime, text} from '../neurological/model';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';
import {asObject} from '../respiratory/respiratoryModel';

export interface WoundScope {
  patient: string;
  encounter: string;
  start: string;
  end: string;
}

const categories = {assessment: 'Assessment', dressing: 'Dressing', pressure_care: 'Pressure care'};

export function woundTitle(source: Evidence) {
  return text(source.fact.title) || 'Wound care record';
}

export function woundCategory(source: Evidence) {
  const category = text(source.fact.category);
  return Object.hasOwn(categories, category) ? categories[category as keyof typeof categories] : 'Wound care record';
}

export function woundStatus(source: Evidence) {
  if (source.fact.record_status === 'withdrawn' || source.fact.report_status === 'withdrawn') return 'Withdrawn source record';
  if (source.fact.conflict === 'unresolved') return 'Unresolved source conflict';
  if (!hasRecordedContent(source)) return 'Source record unconfirmed';
  return source.fact.report_status === 'corrected' ? 'Corrected source record' :
    source.fact.report_status === 'preliminary' || source.fact.report_status === 'interim' ? 'Provisional source record' : '';
}

export function woundMeasurements(source: Evidence) {
  const length = text(source.fact.length_cm);
  const width = text(source.fact.width_cm);
  if (length && width) return length + ' × ' + width + ' cm';
  if (length) return 'Length ' + length + ' cm';
  if (width) return 'Width ' + width + ' cm';
  return '';
}

export function shortWoundTime(value: string) {
  return value.replace(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):00(Z|[+-]\d{2}:\d{2})$/, '$1 · $2 $3');
}

export function woundTime(source: Evidence) {
  return shortWoundTime(sourceTime(source));
}

function scopeMatches(catalog: Catalog, requested: WoundScope) {
  const scope = catalog.combined.context.scope;
  return Array.isArray(catalog.wound_records) &&
    catalog.execution_enabled === false && catalog.combined.execution_enabled === false &&
    catalog.repository === catalog.cutoff.repository_id &&
    scope.repository_cutoff.repository_id === catalog.repository &&
    scope.repository_cutoff.fact_watermark === catalog.cutoff.fact_watermark &&
    scope.patient_id === requested.patient && scope.encounter_id === requested.encounter &&
    compare(scope.review_start, requested.start) === 0 && compare(scope.review_end, requested.end) === 0;
}

function inScope(source: Evidence, catalog: Catalog, requested: WoundScope) {
  const target = source.fact.binding.target;
  const times = asObject(source.fact.times);
  const lastKnown = (field: string) => {
    const time = asObject(times[field]);
    if (time.status !== 'known' || time.precision === 'day') return '';
    return text(time.upper ?? time.value);
  };
  const occurred = lastKnown('occurred');
  return source.fact.kind === 'wound_record' && source.repository === catalog.repository &&
    source.ingestion.repository_id === catalog.repository && source.ingestion.ingestion_sequence <= source.cutoff &&
    source.cutoff <= catalog.cutoff.fact_watermark &&
    target.patient_id === requested.patient && target.encounter_id === requested.encounter &&
    (!occurred || compare(occurred, requested.start) !== -1) &&
    ['occurred', 'reported', 'available'].every(field => compare(lastKnown(field), requested.end) !== 1);
}

export function chartContentAvailable(source: Evidence) {
  return hasRecordedContent(source) && source.fact.conflict !== 'unresolved';
}

function chronological(left: Evidence, right: Evidence) {
  const first = occurredAt(left), second = occurredAt(right);
  if (first && second) return compare(first, second) ?? 0;
  return first ? -1 : second ? 1 : 0;
}

function latestAssessment(assessments: Evidence[]) {
  const sources = assessments.filter(source => occurredAt(source));
  const latest = sources.at(-1);
  return latest && sources.length === assessments.length &&
    !sources.slice(0, -1).some(source => chronological(source, latest) === 0) ? latest : undefined;
}

function pinIdentity(pins: unknown[]) {
  return stable(pins.map(value => {
    const {cutoff: _cutoff, ...identity} = asObject(value);
    return stable(identity);
  }).sort());
}

export function woundModel(catalog: Catalog | undefined, requested: WoundScope) {
  const valid = !!catalog && scopeMatches(catalog, requested);
  const sources = valid ? (catalog.wound_records ?? []).filter(source => inScope(source, catalog, requested)).sort(chronological) : [];
  const groups = new Map<string, Evidence[]>();
  for (const source of sources) {
    const wound = text(source.fact.wound_id);
    if (!wound) continue;
    const group = groups.get(wound);
    if (group) group.push(source);
    else groups.set(wound, [source]);
  }
  const wounds = Array.from(groups, ([id, records]) => ({
    id,
    latest: latestAssessment(records.filter(source => source.fact.category === 'assessment')),
    lastDressing: latestAssessment(records.filter(source => source.fact.category === 'dressing')),
  }));
  const pressureCare = sources.filter(source => source.fact.category === 'pressure_care' && chartContentAvailable(source));
  const pins = sources.map(source => ({
    repository: source.repository, kind: source.fact.kind, id: source.fact.id, version: source.fact.revision,
    digest: source.digest, ingestion: source.ingestion.ingestion_sequence, cutoff: source.cutoff,
  }));
  const signature = valid ? stable(['m15/v1', requested.patient, requested.encounter, requested.start, requested.end, catalog.repository]) : '';
  const identity = stable([signature, pinIdentity(pins)]);
  function matches(review: SavedReview<unknown>) {
    const cutoff = asObject(review.snapshot.cutoff);
    return valid && review.domain === 'M15' && review.patient === requested.patient &&
      review.encounter === requested.encounter && review.repository === catalog.repository &&
      review.snapshot.signature === signature && compare(review.period.start, requested.start) === 0 &&
      compare(review.period.end, requested.end) === 0 && cutoff.repository_id === catalog.repository &&
      Number.isSafeInteger(cutoff.fact_watermark) && Number(cutoff.fact_watermark) <= catalog.cutoff.fact_watermark &&
      review.snapshot.pins.every(value => {
        const retained = asObject(value);
        return retained.repository === catalog.repository && Number(retained.cutoff) >= Number(retained.ingestion) &&
          Number(retained.cutoff) <= Number(cutoff.fact_watermark);
      }) && pinIdentity(review.snapshot.pins) === pinIdentity(pins);
  }

  return {valid, sources, wounds, pressureCare, pins, signature, identity, matches};
}

export type WoundModel = ReturnType<typeof woundModel>;
