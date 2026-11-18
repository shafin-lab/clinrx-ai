import {pin, stable, type Catalog, type Evidence, type Pin} from '../api/rf2Client';
import type {SavedReview} from '../clinical/savedReviewStore';
import {asObject} from '../respiratory/respiratoryModel';
import {compareRespiratoryInstants as compare} from '../respiratory/exactTime';

export interface Requested {patient: string; encounter: string; start: string; end: string}
const relevantLabs = new Set(['phosphate', 'magnesium', 'potassium', 'glucose']);
export const reviewPin = (source: Evidence) => {
  const {reference, ...metadata} = pin(source);
  return {...metadata, ...reference};
};
const revisionIdentity = ({repository, reference, digest, ingestion}: Pin) => stable([repository, reference, digest, ingestion]);

export function savedPin(raw: unknown, repository: string, watermark: number): Pin | undefined {
  const p = asObject(raw);
  if (p.repository !== repository || typeof p.kind !== 'string' || typeof p.id !== 'string' ||
      typeof p.version !== 'string' || typeof p.digest !== 'string' || !/^[a-f0-9]{64}$/.test(p.digest) ||
      typeof p.ingestion !== 'number' || !Number.isSafeInteger(p.ingestion) || p.ingestion < 1 ||
      typeof p.cutoff !== 'number' || !Number.isSafeInteger(p.cutoff) || p.cutoff < p.ingestion || p.cutoff > watermark) return;
  return {repository, reference: {kind: p.kind, id: p.id, version: p.version}, digest: p.digest,
    ingestion: p.ingestion, cutoff: p.cutoff};
}

export function catalogModel(catalog: Catalog | undefined, requested: Requested) {
  const slice = catalog?.combined.context.scope;
  const valid = !!catalog && !!slice && catalog.execution_enabled === false && catalog.combined.execution_enabled === false &&
    catalog.cutoff.repository_id === catalog.repository && slice.repository_cutoff.repository_id === catalog.repository &&
    slice.repository_cutoff.fact_watermark === catalog.cutoff.fact_watermark && slice.patient_id === requested.patient &&
    slice.encounter_id === requested.encounter && compare(slice.review_start, requested.start) === 0 &&
    compare(slice.review_end, requested.end) === 0;
  const bounded = (source: Evidence) => {
    const target = source.fact.binding.target;
    return !!catalog && !source.superseded && source.repository === catalog.repository &&
      source.ingestion.repository_id === catalog.repository && source.ingestion.ingestion_sequence <= source.cutoff &&
      source.cutoff <= catalog.cutoff.fact_watermark && target.patient_id === requested.patient &&
      target.encounter_id === requested.encounter;
  };
  const records = valid ? [
    ...(catalog.nutrition_records ?? []).filter(source => source.fact.kind === 'nutrition_record' && bounded(source)),
    ...(catalog.endocrine_records ?? []).filter(source => source.fact.kind === 'endocrine_record' &&
      source.fact.category === 'nutrition' && bounded(source)),
  ] : [];
  const labs = valid ? catalog.laboratory_reports.filter(source => source.fact.kind === 'laboratory_report' && bounded(source) &&
    Array.isArray(source.fact.components) && source.fact.components.some(raw => {
      const component = asObject(raw);
      return component.mapping_status === 'mapped' && relevantLabs.has(String(component.mapped_concept));
    })) : [];
  const sources = [...records, ...labs];
  const pins = sources.map(reviewPin);
  const signature = stable(['m17/catalog/v1', requested.patient, requested.encounter, requested.start, requested.end, catalog?.repository]);
  const revisions = stable(sources.map(source => revisionIdentity(pin(source))).sort());
  function matches(review: SavedReview<unknown>) {
    if (!valid || review.snapshot.signature !== signature || review.repository !== catalog.repository ||
      review.domain !== 'M17' || review.patient !== requested.patient || review.encounter !== requested.encounter ||
      compare(review.period.start, requested.start) !== 0 || compare(review.period.end, requested.end) !== 0) return false;
    const cutoff = asObject(review.snapshot.cutoff);
    if (cutoff.repository_id !== catalog.repository || typeof cutoff.fact_watermark !== 'number' ||
      !Number.isSafeInteger(cutoff.fact_watermark) || cutoff.fact_watermark > catalog.cutoff.fact_watermark) return false;
    const original = review.snapshot.pins.map(raw => savedPin(raw, catalog.repository, Number(cutoff.fact_watermark)));
    return original.every(p => p !== undefined) && stable(original.map(revisionIdentity).sort()) === revisions;
  }
  return {valid, records, labs, sources, pins, signature, identity: stable([signature, revisions]), matches};
}
