import {compareRespiratoryInstants} from '../respiratory/exactTime';

function record(value: unknown): Record<string, unknown> {
 return value && typeof value === 'object' && !Array.isArray(value)
  ? value as Record<string, unknown>
  : {};
}

export function displayLaboratoryUnit(unit: string): string {
 return unit.trim() === '1' ? '' : unit;
}

export function laboratoryCollection(fact: Record<string, unknown>) {
 const collected = record(record(fact.times).collected);
 if (collected.status === 'known') {
  const value = collected.value;
  if (collected.precision === 'instant' && typeof value === 'string' &&
      compareRespiratoryInstants(value, value) === 0) {
   return {instant: value, text: value};
  }
  if (collected.precision === 'bounded' &&
      typeof collected.lower === 'string' && typeof collected.upper === 'string') {
   return {instant: null, text: `Collection window ${collected.lower} → ${collected.upper}`};
  }
  if (typeof value === 'string' && collected.precision === 'approximate') {
   return {instant: null, text: `Approximate collection time ${value}`};
  }
  if (typeof value === 'string' && collected.precision === 'day') {
   return {instant: null, text: `Collection date ${value.slice(0, 10)}`};
  }
 }
 return {instant: null, text: collected.status === 'unknown'
  ? 'Collection time unknown'
  : 'Collection time not recorded'};
}

export function compareLaboratoryCollections(left: string | null, right: string | null): number {
 if (left && right) return compareRespiratoryInstants(right, left) ?? 0;
 return left ? -1 : right ? 1 : 0;
}

export function hasUniqueLatestCollection(times: (string | null)[]): boolean {
 const first = times[0];
 return !!first && times.slice(1).every(time => !!time && compareRespiratoryInstants(first, time) === 1);
}
