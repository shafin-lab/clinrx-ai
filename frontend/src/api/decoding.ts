/** Pure transport validation. No fetching, clinical policy, defaults, or normalization. */
export class DecodeFailure extends Error {
  readonly code = 'invalid_response';
  constructor() { super('The server response could not be read safely.'); this.name = 'DecodeFailure'; }
}
export function reject(): never { throw new DecodeFailure(); }
export interface Schema {
  readonly $ref?: string; readonly type?: string; readonly const?: unknown;
  readonly enum?: readonly unknown[]; readonly properties?: Readonly<Record<string, Schema>>;
  readonly required?: readonly string[]; readonly additionalProperties?: boolean;
  readonly anyOf?: readonly Schema[]; readonly oneOf?: readonly Schema[];
  readonly discriminator?: { readonly propertyName: string; readonly mapping: Readonly<Record<string, string>> };
  readonly items?: Schema; readonly prefixItems?: readonly Schema[];
  readonly minItems?: number; readonly maxItems?: number;
  readonly minLength?: number; readonly maxLength?: number; readonly pattern?: string; readonly format?: string;
  readonly minimum?: number; readonly maximum?: number; readonly exclusiveMinimum?: number;
}
export function object(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return reject();
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return reject();
  if (Object.getOwnPropertySymbols(value).length) return reject();
  for (const descriptor of Object.values(Object.getOwnPropertyDescriptors(value))) {
    if (!descriptor.enumerable || !('value' in descriptor)) return reject();
  }
  return value as Record<string, unknown>;
}
/** Validate calendar/offset fields without Date's millisecond truncation or UTC rewriting. */
export function timestamp(value: unknown): string {
  if (typeof value !== 'string') return reject();
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!m) return reject();
  const [year, month, day, hour, minute, second] = m.slice(1, 7).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month-1] || hour > 23 || minute > 59 || second > 59) return reject();
  if (m[8] !== 'Z' && (Number(m[8].slice(1, 3)) > 23 || Number(m[8].slice(4, 6)) > 59)) return reject();
  return value;
}
export function uuid(value: unknown): string {
  if (typeof value !== 'string' || !/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(value)) return reject();
  return value;
}
function referenceName(ref: string): keyof typeof contracts {
  if (!ref.startsWith('#/$defs/')) return reject();
  const key = ref.slice(8);
  if (!Object.hasOwn(contracts, key)) return reject();
  return key as keyof typeof contracts;
}
function matches(value: unknown, schema: Schema, depth: number): boolean {
  try { validate(value, schema, depth); return true; } catch { return false; }
}
function validate(value: unknown, schema: Schema, depth = 0): void {
  if (depth > 64) return reject();
  if (schema.$ref) { const name=referenceName(schema.$ref); validate(value, contracts[name], depth+1); structure(name,value); return; }
  if (Object.hasOwn(schema, 'const') && value !== schema.const) return reject();
  if (schema.enum && !schema.enum.includes(value)) return reject();
  if (schema.discriminator) {
    const tag = object(value)[schema.discriminator.propertyName];
    if (typeof tag !== 'string' || !Object.hasOwn(schema.discriminator.mapping, tag)) return reject();
    return validate(value, {$ref:schema.discriminator.mapping[tag]}, depth+1);
  }
  if (schema.anyOf) { if (!schema.anyOf.some(s=>matches(value,s,depth+1))) reject(); return; }
  if (schema.oneOf) { if (schema.oneOf.filter(s=>matches(value,s,depth+1)).length !== 1) reject(); return; }
  switch (schema.type) {
    case 'null': if (value !== null) reject(); return;
    case 'boolean': if (typeof value !== 'boolean') reject(); return;
    case 'integer':
    case 'number':
      if (typeof value !== 'number' || !Number.isFinite(value) || (schema.type === 'integer' && !Number.isSafeInteger(value))) return reject();
      if (schema.minimum !== undefined && value < schema.minimum || schema.maximum !== undefined && value > schema.maximum || schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) reject();
      return;
    case 'string': {
      if (typeof value !== 'string') return reject();
      const length = Array.from(value).length;
      if (schema.minLength !== undefined && length < schema.minLength || schema.maxLength !== undefined && length > schema.maxLength) reject();
      if (schema.pattern) {
        // Python's end anchor rejects trailing newlines; JavaScript's $ otherwise accepts them.
        const match = new RegExp(schema.pattern).exec(value);
        if (!match || schema.pattern.endsWith('$') && match.index + match[0].length !== value.length) reject();
      }
      if (schema.format === 'date-time') timestamp(value);
      else if (schema.format === 'uuid') uuid(value);
      else if (schema.format !== undefined) reject();
      return;
    }
    case 'array': {
      if (!Array.isArray(value)) return reject();
      if (schema.minItems !== undefined && value.length < schema.minItems || schema.maxItems !== undefined && value.length > schema.maxItems) reject();
      if (Object.keys(value).length !== value.length) reject();
      for (let i=0;i<value.length;i++) {
        if (!Object.hasOwn(value,i)) reject();
        const descriptor = Object.getOwnPropertyDescriptor(value,String(i));
        if (!descriptor || !('value' in descriptor)) reject();
        const child = schema.prefixItems?.[i] ?? schema.items;
        if (!child) reject();
        validate(descriptor.value,child,depth+1);
      }
      return;
    }
    case 'object': {
      const record = object(value), properties = schema.properties ?? {};
      for (const key of schema.required ?? []) if (!Object.hasOwn(record,key)) reject();
      for (const [key,child] of Object.entries(record)) {
        if (!Object.hasOwn(properties,key)) { if (schema.additionalProperties === false) reject(); }
        else validate(child,properties[key],depth+1);
      }
      return;
    }
    default: return reject();
  }
}
// Types are inferred from the same backend-derived structural definitions, not a second manual hierarchy.
type RefName<R> = R extends `#/$defs/${infer Name}` ? Name : never;
type Infer<S> = S extends {readonly $ref:infer R} ? RefName<R> extends keyof typeof contracts ? Infer<(typeof contracts)[RefName<R>]> : never
  : S extends {readonly const:infer V} ? V
  : S extends {readonly enum:readonly (infer V)[]} ? V
  : S extends {readonly anyOf:readonly (infer V)[]} ? Infer<V>
  : S extends {readonly oneOf:readonly (infer V)[]} ? Infer<V>
  : S extends {readonly type:'null'} ? null
  : S extends {readonly type:'string'} ? string
  : S extends {readonly type:'integer'|'number'} ? number
  : S extends {readonly type:'boolean'} ? boolean
  : S extends {readonly prefixItems:infer P extends readonly unknown[]} ? {-readonly [K in keyof P]:Infer<P[K]>}
  : S extends {readonly type:'array'; readonly items:infer I} ? Infer<I>[]
  : S extends {readonly type:'object'; readonly properties:infer P} ?
    {[K in keyof P as K extends RequiredKeys<S> ? K : never]:Infer<P[K]>} & {[K in keyof P as K extends RequiredKeys<S> ? never : K]?:Infer<P[K]>}
  : never;
type RequiredKeys<S> = S extends {readonly required:readonly (infer K)[]} ? K : never;
export type Decoded<Name extends keyof typeof contracts> = Infer<(typeof contracts)[Name]>;
export function decodeContract<Name extends keyof typeof contracts>(name: Name, value: unknown, correspondence?: (value:Record<string,unknown>)=>void): Decoded<Name> {
  try {
    validate(value,contracts[name]);
    structure(name,value);
    correspondence?.(object(value));
    return value as Decoded<Name>;
  } catch { throw new DecodeFailure(); }
}
export interface ScopeIdentity { patient_id?: string; encounter_id?: string }
export interface ExecutionIdentity { execution_id?: string; inference_reference?: {kind:string; id:string; version:string} }
export function scopeIdentity(value: unknown, expected: ScopeIdentity = {}): void {
  const scope = object(value);
  if (expected.patient_id !== undefined && scope.patient_id !== expected.patient_id || expected.encounter_id !== undefined && scope.encounter_id !== expected.encounter_id) reject();
}
export function executionIdentity(value: Record<string,unknown>, expected: ExecutionIdentity = {}): void {
  if (expected.execution_id !== undefined && value.execution_id !== expected.execution_id) reject();
}
export function ref(value: unknown): {kind:string;id:string;version:string} {
  const r = object(value);
  for (const k of ['kind','id','version']) if (typeof r[k] !== 'string' || !r[k]) reject();
  return r as {kind:string;id:string;version:string};
}
export function factRef(value: unknown, defaultKind?:string) { const f=object(value); return ref({kind:f.kind??defaultKind,id:f.id,version:f.revision}); }
export function sameRef(a: unknown,b: unknown): boolean { const x=ref(a),y=ref(b);return x.kind===y.kind && x.id===y.id && x.version===y.version; }
export function requireRef(a: unknown,b: unknown): void { if(!sameRef(a,b)) reject(); }
export function stableRef(a: unknown,b: unknown): void { const x=ref(a),y=ref(b);if(x.kind!==y.kind || x.id!==y.id) reject(); }
export function array(value:unknown): unknown[] { if(!Array.isArray(value))return reject();return value; }
export function tuple(value:unknown,length:number): unknown[] { const a=array(value);if(a.length!==length)reject();return a; }
export function distinctReferences(values: readonly unknown[]): void {
  const keys=values.map(value=>{const r=ref(value);return JSON.stringify([r.kind,r.id,r.version]);});
  if(new Set(keys).size!==keys.length)reject();
}

// Post-schema checks below express representation coherence only. They never establish eligibility.
function structure(name:string,value:unknown):void {
  if(name==='RecordedTime') {
    const t=object(value),status=t.status,precision=t.precision??'unknown';
    const present=(key:string)=>t[key]!==null && t[key]!==undefined;
    if(status!=='known') {
      if(precision!=='unknown' || ['value','lower','upper'].some(present))reject();
    } else if(precision==='bounded') {
      if(!present('lower') || !present('upper'))reject();
      if(instant(t.lower)>instant(t.upper))reject();
      if(present('value') && (instant(t.value)<instant(t.lower) || instant(t.value)>instant(t.upper)))reject();
    } else if(['instant','day','approximate'].includes(String(precision))) {
      if(!present('value') || present('lower') || present('upper') || precision==='approximate' && !t.uncertainty)reject();
    } else reject();
  }
  if(name==='DomainBinding') {
    const b=object(value), candidates=array(b.candidates??[]),exact=b.exact,stable=b.stable_target;
    if(b.status==='resolved') {if(exact===null || exact===undefined || stable===null || stable===undefined || candidates.length)reject();}
    else if(exact!==undefined && exact!==null || !b.limitation)reject();
    if(b.status==='ambiguous' && candidates.length<2 || b.status==='unresolved' && candidates.length)reject();
    distinctReferences(candidates);
    const allowed:Record<string,string[]>={specimen:['microbiology_specimen'],isolate:['microbiology_isolate'],collection_set:['blood_culture_set'],bottle:['blood_culture_bottle'],order:['antimicrobial_order','medication_order']};
    const kinds=allowed[b.role as string];
    if(stable!==null && stable!==undefined && !kinds.includes(object(stable).kind as string))reject();
    for(const r of [...candidates,...(exact===null || exact===undefined?[]:[exact])]) {
      if(!kinds.includes(ref(r).kind))reject();
      if(stable!==null && stable!==undefined)stableRef(r,{...object(stable),version:ref(r).version});
    }
  }
}
// Exact integer microseconds are used solely for validating an explicitly supplied time interval.
function instant(value:unknown):bigint {
  const text=timestamp(value),m=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(text)!;
  const [year,month,day,hour,minute,second]=m.slice(1,7).map(Number);
  const y=year-1,leap=year%4===0 && (year%100!==0 || year%400===0);
  const before=[0,31,59,90,120,151,181,212,243,273,304,334];
  const days=365*y+Math.floor(y/4)-Math.floor(y/100)+Math.floor(y/400)+before[month-1]+(leap&&month>2?1:0)+day-1;
  const offset=m[8]==='Z'?0:(Number(m[8].slice(1,3))*60+Number(m[8].slice(4,6)))*(m[8][0]==='-'?-1:1);
  return BigInt(((days*24+hour)*60+minute-offset)*60+second)*1000000n+BigInt((m[7]??'').padEnd(6,'0'));
}

/** Generated from the 76bc7f9 backend serialization schemas. Titles/descriptions/default values
 * are omitted; required/nullable/extra-field policies and every public field are retained.
 * This is a pinned contract snapshot, not a general JSON Schema implementation. */
const contracts = {
  "CoverageView": {
    "additionalProperties": false,
    "properties": {
      "domain": {
        "enum": [
          "laboratory",
          "medication",
          "antimicrobial",
          "hemodynamic_support",
          "respiratory_support",
          "renal_support",
          "fluid_output",
          "microbiology",
          "procedure",
          "history_event"
        ],
        "type": "string"
      },
      "mapping_support": {
        "enum": [
          "supported",
          "partial",
          "unsupported"
        ],
        "type": "string"
      },
      "retrieval": {
        "enum": [
          "completed",
          "not_attempted"
        ],
        "type": "string"
      },
      "candidate_count": {
        "anyOf": [
          {
            "minimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "retained_count": {
        "anyOf": [
          {
            "minimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "unsuitable_count": {
        "anyOf": [
          {
            "minimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "source_completeness": {
        "const": "unknown",
        "type": "string"
      },
      "limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "domain",
      "mapping_support",
      "retrieval",
      "limitations"
    ],
    "type": "object"
  },
  "CutoffView": {
    "additionalProperties": false,
    "properties": {
      "repository_id": {
        "format": "uuid",
        "type": "string"
      },
      "fact_watermark": {
        "minimum": 0,
        "type": "integer"
      },
      "captured_at": {
        "format": "date-time",
        "type": "string"
      }
    },
    "required": [
      "repository_id",
      "fact_watermark",
      "captured_at"
    ],
    "type": "object"
  },
  "ExactReference": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "id": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "kind",
      "id",
      "version"
    ],
    "type": "object"
  },
  "LaboratoryView": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "selection_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "time": {
        "$ref": "#/$defs/TimesView"
      },
      "source": {
        "$ref": "#/$defs/SourceView"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "verification": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "conflict": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "temporal_status": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "provenance_recorded_at": {
        "format": "date-time",
        "type": "string"
      },
      "provenance_actor": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "provenance_limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "provenance_completeness": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "ingested_at": {
        "format": "date-time",
        "type": "string"
      },
      "disclosures": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "domain": {
        "const": "laboratory",
        "type": "string"
      },
      "concept_id": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "quantity": {
        "$ref": "#/$defs/QuantityView"
      }
    },
    "required": [
      "reference",
      "selection_digest",
      "time",
      "source",
      "origin",
      "verification",
      "conflict",
      "temporal_status",
      "provenance_recorded_at",
      "provenance_completeness",
      "ingested_at",
      "disclosures",
      "concept_id",
      "quantity"
    ],
    "type": "object"
  },
  "MappingIssueView": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "domain": {
        "anyOf": [
          {
            "enum": [
              "laboratory",
              "medication"
            ],
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "reason": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "reference",
      "domain",
      "reason"
    ],
    "type": "object"
  },
  "MedicationView": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "selection_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "time": {
        "$ref": "#/$defs/TimesView"
      },
      "source": {
        "$ref": "#/$defs/SourceView"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "verification": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "conflict": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "temporal_status": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "provenance_recorded_at": {
        "format": "date-time",
        "type": "string"
      },
      "provenance_actor": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "provenance_limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "provenance_completeness": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "ingested_at": {
        "format": "date-time",
        "type": "string"
      },
      "disclosures": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "domain": {
        "const": "medication",
        "type": "string"
      },
      "event_type": {
        "enum": [
          "medication_order",
          "medication_administration"
        ],
        "type": "string"
      },
      "product_id": {
        "anyOf": [
          {
            "maxLength": 256,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "ingredient_ids": {
        "items": {
          "maxLength": 256,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "formulation": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "status": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "dose": {
        "anyOf": [
          {
            "$ref": "#/$defs/QuantityView"
          },
          {
            "type": "null"
          }
        ]
      },
      "dose_basis": {
        "anyOf": [
          {
            "maxLength": 256,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "route": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "schedule_text": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "frequency_occurrences": {
        "anyOf": [
          {
            "exclusiveMinimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "frequency_interval": {
        "anyOf": [
          {
            "$ref": "#/$defs/QuantityView"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "reference",
      "selection_digest",
      "time",
      "source",
      "origin",
      "verification",
      "conflict",
      "temporal_status",
      "provenance_recorded_at",
      "provenance_completeness",
      "ingested_at",
      "disclosures",
      "event_type",
      "status"
    ],
    "type": "object"
  },
  "QuantityView": {
    "additionalProperties": false,
    "properties": {
      "value": {
        "maxLength": 128,
        "pattern": "^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$",
        "type": "string"
      },
      "unit_raw": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "unit_code": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "unit_system": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "unit_status": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "value",
      "unit_raw",
      "unit_status"
    ],
    "type": "object"
  },
  "ScopeView": {
    "additionalProperties": false,
    "properties": {
      "patient_id": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "encounter_id": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "review_start": {
        "format": "date-time",
        "type": "string"
      },
      "review_end": {
        "format": "date-time",
        "type": "string"
      },
      "repository_cutoff": {
        "$ref": "#/$defs/CutoffView"
      }
    },
    "required": [
      "patient_id",
      "encounter_id",
      "review_start",
      "review_end",
      "repository_cutoff"
    ],
    "type": "object"
  },
  "SourceView": {
    "additionalProperties": false,
    "properties": {
      "namespace": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "identifier": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "anyOf": [
          {
            "maxLength": 256,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "channel": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "namespace",
      "identifier",
      "channel"
    ],
    "type": "object"
  },
  "TimesView": {
    "additionalProperties": false,
    "properties": {
      "event": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "effective_start": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "effective_end": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "recorded": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "retrieved": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "processed": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "precision": {
        "maxLength": 256,
        "minLength": 1,
        "type": "string"
      },
      "uncertainty": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "precision"
    ],
    "type": "object"
  },
  "PatientStateViewResponse": {
    "additionalProperties": false,
    "properties": {
      "transport_version": {
        "const": "1",
        "type": "string"
      },
      "scope": {
        "$ref": "#/$defs/ScopeView"
      },
      "state_context": {
        "maxLength": 65536,
        "minLength": 1,
        "pattern": "^[A-Za-z0-9_.=-]+$",
        "type": "string"
      },
      "profile_id": {
        "const": "SyntheticLaboratoryMedicationState",
        "type": "string"
      },
      "profile_version": {
        "const": "1",
        "type": "string"
      },
      "laboratory": {
        "items": {
          "$ref": "#/$defs/LaboratoryView"
        },
        "maxItems": 1000,
        "type": "array"
      },
      "medication": {
        "items": {
          "$ref": "#/$defs/MedicationView"
        },
        "maxItems": 1000,
        "type": "array"
      },
      "coverage": {
        "items": {
          "$ref": "#/$defs/CoverageView"
        },
        "maxItems": 10,
        "minItems": 10,
        "type": "array"
      },
      "issues": {
        "items": {
          "$ref": "#/$defs/MappingIssueView"
        },
        "maxItems": 2000,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "scope",
      "state_context",
      "laboratory",
      "medication",
      "coverage",
      "issues",
      "disclosures"
    ],
    "type": "object"
  },
  "PreparedTemporalReviewResponse": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "const": "prepared",
        "type": "string"
      },
      "execution_id": {
        "format": "uuid",
        "type": "string"
      },
      "inference_reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "command": {
        "maxLength": 65536,
        "minLength": 1,
        "pattern": "^[A-Za-z0-9_.=-]+$",
        "type": "string"
      }
    },
    "required": [
      "execution_id",
      "inference_reference",
      "command"
    ],
    "type": "object"
  },
  "ContextView": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "completeness": {
        "const": "partial",
        "type": "string"
      },
      "evidence_references": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          }
        ],
        "type": "array"
      },
      "limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "reference",
      "evidence_references",
      "limitations"
    ],
    "type": "object"
  },
  "DirectDependencyView": {
    "additionalProperties": false,
    "properties": {
      "target": {
        "$ref": "#/$defs/ExactReference"
      },
      "relationship": {
        "const": "derived_from",
        "type": "string"
      }
    },
    "required": [
      "target"
    ],
    "type": "object"
  },
  "GovernanceView": {
    "additionalProperties": false,
    "properties": {
      "outcome": {
        "enum": [
          "released",
          "withheld"
        ],
        "type": "string"
      },
      "decision_reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "decided_at": {
        "format": "date-time",
        "type": "string"
      },
      "assessed_at": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "reasons": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "safety_status": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "fidelity_status": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "freshness_status": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "authority_status": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "outcome",
      "decision_reference",
      "decided_at",
      "reasons",
      "safety_status",
      "fidelity_status",
      "freshness_status",
      "authority_status",
      "limitations"
    ],
    "type": "object"
  },
  "InferenceView": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "method": {
        "$ref": "#/$defs/ExactReference"
      },
      "statement": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "applicability": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "limitations": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "inputs": {
        "maxItems": 3,
        "minItems": 3,
        "prefixItems": [
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          }
        ],
        "type": "array"
      }
    },
    "required": [
      "reference",
      "method",
      "applicability",
      "uncertainty",
      "limitations",
      "inputs"
    ],
    "type": "object"
  },
  "ProvenanceView": {
    "additionalProperties": false,
    "properties": {
      "inference": {
        "$ref": "#/$defs/InferenceView"
      },
      "earlier_laboratory": {
        "$ref": "#/$defs/LaboratoryView"
      },
      "later_laboratory": {
        "$ref": "#/$defs/LaboratoryView"
      },
      "medication": {
        "$ref": "#/$defs/MedicationView"
      },
      "terminal_references": {
        "maxItems": 3,
        "minItems": 3,
        "prefixItems": [
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          },
          {
            "$ref": "#/$defs/ExactReference"
          }
        ],
        "type": "array"
      },
      "inference_terminal_reference": {
        "$ref": "#/$defs/ExactReference"
      },
      "direct_dependencies": {
        "maxItems": 3,
        "minItems": 3,
        "prefixItems": [
          {
            "$ref": "#/$defs/DirectDependencyView"
          },
          {
            "$ref": "#/$defs/DirectDependencyView"
          },
          {
            "$ref": "#/$defs/DirectDependencyView"
          }
        ],
        "type": "array"
      },
      "input_cutoff": {
        "$ref": "#/$defs/CutoffView"
      },
      "inference_cutoff": {
        "$ref": "#/$defs/CutoffView"
      },
      "final_cutoff": {
        "$ref": "#/$defs/CutoffView"
      },
      "final_recheck": {
        "enum": [
          "unchanged",
          "materially_changed",
          "unavailable"
        ],
        "type": "string"
      },
      "recheck_reasons": {
        "items": {
          "maxLength": 4096,
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "inference",
      "earlier_laboratory",
      "later_laboratory",
      "medication",
      "terminal_references",
      "inference_terminal_reference",
      "direct_dependencies",
      "input_cutoff",
      "inference_cutoff",
      "final_cutoff",
      "final_recheck",
      "recheck_reasons"
    ],
    "type": "object"
  },
  "TemporalExecutionResponse": {
    "additionalProperties": false,
    "properties": {
      "transport_version": {
        "const": "1",
        "type": "string"
      },
      "execution_id": {
        "format": "uuid",
        "type": "string"
      },
      "status": {
        "const": "completed",
        "type": "string"
      },
      "finalized_at": {
        "format": "date-time",
        "type": "string"
      },
      "ingested_at": {
        "format": "date-time",
        "type": "string"
      },
      "context": {
        "$ref": "#/$defs/ContextView"
      },
      "governance": {
        "$ref": "#/$defs/GovernanceView"
      },
      "provenance": {
        "$ref": "#/$defs/ProvenanceView"
      }
    },
    "required": [
      "execution_id",
      "finalized_at",
      "ingested_at",
      "context",
      "governance",
      "provenance"
    ],
    "type": "object"
  },
  "ReconciliationResponse": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "enum": [
          "committed_match",
          "absent"
        ],
        "type": "string"
      },
      "execution": {
        "anyOf": [
          {
            "$ref": "#/$defs/TemporalExecutionResponse"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "status",
      "execution"
    ],
    "type": "object"
  },
  "AntimicrobialIdentity": {
    "additionalProperties": false,
    "properties": {
      "identity_version": {
        "const": "1",
        "type": "string"
      },
      "source_code": {
        "$ref": "#/$defs/SourceCode"
      },
      "raw_display": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "canonical_id": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "ingredient_ids": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 16,
        "type": "array"
      },
      "product": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "formulation": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "mapping_status": {
        "enum": [
          "mapped",
          "unknown",
          "unsupported",
          "ambiguous"
        ],
        "type": "string"
      },
      "mapping_provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "limitation": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "source_code",
      "raw_display",
      "mapping_status",
      "mapping_provenance"
    ],
    "type": "object"
  },
  "AntimicrobialNonDelivery": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "antimicrobial_non_delivery",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "antimicrobial": {
        "$ref": "#/$defs/AntimicrobialIdentity"
      },
      "status": {
        "enum": [
          "held",
          "refused",
          "missed",
          "cancelled",
          "not_given",
          "other"
        ],
        "type": "string"
      },
      "occurred": {
        "$ref": "#/$defs/RecordedTime"
      },
      "recorded_reason": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "other_status": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "antimicrobial",
      "status"
    ],
    "type": "object"
  },
  "AntimicrobialOrder": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "antimicrobial_order",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "antimicrobial": {
        "$ref": "#/$defs/AntimicrobialIdentity"
      },
      "prescribed_dose": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedDose"
          },
          {
            "type": "null"
          }
        ]
      },
      "route": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "frequency": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedFrequency"
          },
          {
            "type": "null"
          }
        ]
      },
      "schedule": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "scheduling": {
        "enum": [
          "standing",
          "prn",
          "unknown"
        ],
        "type": "string"
      },
      "recorded_indication": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "therapy_purpose": {
        "anyOf": [
          {
            "$ref": "#/$defs/DocumentedTherapyPurpose"
          },
          {
            "type": "null"
          }
        ]
      },
      "order_status": {
        "enum": [
          "draft",
          "active",
          "held",
          "cancelled",
          "completed",
          "discontinued",
          "unknown"
        ],
        "type": "string"
      },
      "created": {
        "$ref": "#/$defs/RecordedTime"
      },
      "intended_start": {
        "$ref": "#/$defs/RecordedTime"
      },
      "intended_end": {
        "$ref": "#/$defs/RecordedTime"
      },
      "discontinued": {
        "$ref": "#/$defs/RecordedTime"
      },
      "discontinuation_reason": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "antimicrobial",
      "order_status"
    ],
    "type": "object"
  },
  "AntimicrobialView": {
    "additionalProperties": false,
    "properties": {
      "orders": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 512,
        "type": "array"
      },
      "administrations": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 512,
        "type": "array"
      },
      "non_delivery": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 512,
        "type": "array"
      }
    },
    "type": "object"
  },
  "AssemblyIssueV2": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/Reference"
      },
      "reason": {
        "enum": [
          "unsupported_source_structure",
          "withdrawn_terminal",
          "outside_review_window",
          "temporal_incompleteness",
          "contextual_parent",
          "unresolved_parent",
          "ambiguous_binding",
          "historical_target_not_retained",
          "withdrawn_binding_target",
          "unsupported_antimicrobial_mapping",
          "preliminary_report",
          "incomplete_susceptibility",
          "unknown_isolate_identity"
        ],
        "type": "string"
      }
    },
    "required": [
      "reference",
      "reason"
    ],
    "type": "object"
  },
  "AssemblyLimits": {
    "additionalProperties": false,
    "properties": {
      "history": {
        "$ref": "#/$defs/HistoryBudget"
      },
      "max_items": {
        "maximum": 512,
        "minimum": 1,
        "type": "integer"
      },
      "max_specimens": {
        "maximum": 128,
        "minimum": 1,
        "type": "integer"
      },
      "max_isolates": {
        "maximum": 256,
        "minimum": 1,
        "type": "integer"
      },
      "max_children": {
        "maximum": 64,
        "minimum": 1,
        "type": "integer"
      },
      "max_molecular_targets": {
        "maximum": 64,
        "minimum": 1,
        "type": "integer"
      },
      "max_bindings": {
        "maximum": 1024,
        "minimum": 1,
        "type": "integer"
      },
      "max_depth": {
        "maximum": 8,
        "minimum": 0,
        "type": "integer"
      },
      "max_fanout": {
        "maximum": 16,
        "minimum": 1,
        "type": "integer"
      },
      "max_traversal_steps": {
        "maximum": 8192,
        "minimum": 1,
        "type": "integer"
      },
      "max_issues": {
        "maximum": 512,
        "minimum": 1,
        "type": "integer"
      },
      "max_result_bytes": {
        "maximum": 16777216,
        "minimum": 1,
        "type": "integer"
      }
    },
    "type": "object"
  },
  "AssemblyRequestV2": {
    "additionalProperties": false,
    "properties": {
      "scope": {
        "$ref": "#/$defs/PatientStateScopeV2"
      },
      "profile_id": {
        "const": "SyntheticMicrobiologyAntimicrobialState",
        "type": "string"
      },
      "profile_version": {
        "const": "2",
        "type": "string"
      },
      "limits": {
        "$ref": "#/$defs/AssemblyLimits"
      }
    },
    "required": [
      "scope",
      "profile_id",
      "profile_version"
    ],
    "type": "object"
  },
  "Binding": {
    "additionalProperties": false,
    "properties": {
      "target": {
        "$ref": "#/$defs/ContextTarget"
      },
      "verification": {
        "$ref": "#/$defs/IdentityVerification"
      }
    },
    "required": [
      "target",
      "verification"
    ],
    "type": "object"
  },
  "BindingOutcomeV2": {
    "additionalProperties": false,
    "properties": {
      "owner": {
        "$ref": "#/$defs/Reference"
      },
      "role": {
        "enum": [
          "specimen",
          "isolate",
          "collection_set",
          "bottle",
          "order"
        ],
        "type": "string"
      },
      "declared": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "status": {
        "enum": [
          "resolved",
          "unresolved",
          "ambiguous"
        ],
        "type": "string"
      },
      "disposition": {
        "enum": [
          "retained_exact",
          "historical_exact_not_retained",
          "unavailable_in_prefix",
          "declared_unresolved",
          "declared_ambiguous",
          "outside_profile",
          "withdrawn_target_not_retained"
        ],
        "type": "string"
      },
      "candidates": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 16,
        "type": "array"
      }
    },
    "required": [
      "owner",
      "role",
      "status",
      "disposition"
    ],
    "type": "object"
  },
  "BloodCultureBottle": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "blood_culture_bottle",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "bottle_identifier": {
        "$ref": "#/$defs/SourceCode"
      },
      "bottle_type": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "bottle_role": {
        "enum": [
          "aerobic",
          "anaerobic",
          "pediatric",
          "other",
          "unknown"
        ],
        "type": "string"
      },
      "positive_at": {
        "$ref": "#/$defs/RecordedTime"
      },
      "reported_time_to_positivity": {
        "anyOf": [
          {
            "$ref": "#/$defs/PositiveQuantity"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "bottle_identifier",
      "bottle_type",
      "bottle_role"
    ],
    "type": "object"
  },
  "BloodCultureSet": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "blood_culture_set",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "set_identifier": {
        "$ref": "#/$defs/SourceCode"
      },
      "collected": {
        "$ref": "#/$defs/RecordedTime"
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "set_identifier"
    ],
    "type": "object"
  },
  "BoundedProvenance": {
    "additionalProperties": false,
    "properties": {
      "source": {
        "$ref": "#/$defs/Source"
      },
      "actor": {
        "minLength": 1,
        "type": "string"
      },
      "recorded_at": {
        "format": "date-time",
        "type": "string"
      },
      "upstream": {
        "items": {
          "$ref": "#/$defs/LineageEdge"
        },
        "maxItems": 32,
        "type": "array"
      },
      "lineage": {
        "enum": [
          "complete",
          "incomplete",
          "unknown"
        ],
        "type": "string"
      },
      "limitations": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      }
    },
    "required": [
      "source",
      "actor",
      "recorded_at",
      "lineage"
    ],
    "type": "object"
  },
  "BreakpointContext": {
    "additionalProperties": false,
    "properties": {
      "authority": {
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "source_reference": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "authority"
    ],
    "type": "object"
  },
  "ClinicalTime": {
    "additionalProperties": false,
    "properties": {
      "event": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "recorded": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "effective_start": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "effective_end": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "retrieved": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "processed": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "precision": {
        "enum": [
          "instant",
          "day",
          "approximate",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "precision"
    ],
    "type": "object"
  },
  "CompletedAntimicrobialAdministration": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "antimicrobial_administration",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "antimicrobial": {
        "$ref": "#/$defs/AntimicrobialIdentity"
      },
      "administered_dose": {
        "$ref": "#/$defs/RecordedDose"
      },
      "route": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "completion": {
        "const": "completed",
        "type": "string"
      },
      "administered": {
        "$ref": "#/$defs/RecordedTime"
      },
      "infusion_start": {
        "$ref": "#/$defs/RecordedTime"
      },
      "infusion_end": {
        "$ref": "#/$defs/RecordedTime"
      },
      "therapy_purpose": {
        "anyOf": [
          {
            "$ref": "#/$defs/DocumentedTherapyPurpose"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "antimicrobial",
      "administered_dose"
    ],
    "type": "object"
  },
  "ContextTarget": {
    "additionalProperties": false,
    "properties": {
      "patient_id": {
        "minLength": 1,
        "type": "string"
      },
      "encounter_id": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "longitudinal_context_id": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "patient_id"
    ],
    "type": "object"
  },
  "CoverageV2": {
    "additionalProperties": false,
    "properties": {
      "domain": {
        "enum": [
          "microbiology",
          "antimicrobial"
        ],
        "type": "string"
      },
      "mapping_support": {
        "enum": [
          "supported",
          "partial",
          "unsupported"
        ],
        "type": "string"
      },
      "retrieval": {
        "enum": [
          "completed",
          "not_attempted",
          "limit_exceeded"
        ],
        "type": "string"
      },
      "candidate_count": {
        "anyOf": [
          {
            "minimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "retained_count": {
        "anyOf": [
          {
            "minimum": 0,
            "type": "integer"
          },
          {
            "type": "null"
          }
        ]
      },
      "source_completeness": {
        "const": "unknown",
        "type": "string"
      },
      "limitations": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "minItems": 1,
        "type": "array"
      }
    },
    "required": [
      "domain",
      "mapping_support",
      "retrieval",
      "limitations"
    ],
    "type": "object"
  },
  "CultureFinding": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_culture",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "growth": {
        "enum": [
          "growth",
          "no_growth",
          "indeterminate"
        ],
        "type": "string"
      },
      "quantity": {
        "anyOf": [
          {
            "$ref": "#/$defs/NonnegativeQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "semiquantitation": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "recorded_interpretation": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "growth"
    ],
    "type": "object"
  },
  "DirectExamination": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_direct_examination",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "examination_type": {
        "enum": [
          "gram_stain",
          "microscopy",
          "other"
        ],
        "type": "string"
      },
      "other_type": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "findings": {
        "items": {
          "$ref": "#/$defs/ExaminationFinding"
        },
        "maxItems": 32,
        "minItems": 1,
        "type": "array"
      },
      "method": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "examined": {
        "$ref": "#/$defs/RecordedTime"
      },
      "source_note": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "examination_type",
      "findings"
    ],
    "type": "object"
  },
  "DocumentedTherapyPurpose": {
    "additionalProperties": false,
    "properties": {
      "category": {
        "enum": [
          "empiric",
          "targeted",
          "prophylactic",
          "definitive",
          "suppression"
        ],
        "type": "string"
      },
      "source_wording": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      }
    },
    "required": [
      "category",
      "source_wording",
      "provenance"
    ],
    "type": "object"
  },
  "DomainBinding": {
    "additionalProperties": false,
    "properties": {
      "role": {
        "enum": [
          "specimen",
          "isolate",
          "collection_set",
          "bottle",
          "order"
        ],
        "type": "string"
      },
      "scope": {
        "$ref": "#/$defs/ContextTarget"
      },
      "status": {
        "enum": [
          "resolved",
          "unresolved",
          "ambiguous"
        ],
        "type": "string"
      },
      "stable_target": {
        "anyOf": [
          {
            "$ref": "#/$defs/StableIdentity"
          },
          {
            "type": "null"
          }
        ]
      },
      "exact": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "candidates": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 16,
        "type": "array"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "limitation": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "role",
      "scope",
      "status",
      "provenance"
    ],
    "type": "object"
  },
  "ExaminationFinding": {
    "additionalProperties": false,
    "properties": {
      "category": {
        "enum": [
          "gram_reaction",
          "morphology",
          "cellular",
          "organism_seen",
          "other"
        ],
        "type": "string"
      },
      "finding": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "presence": {
        "enum": [
          "present",
          "absent",
          "indeterminate",
          "not_reported"
        ],
        "type": "string"
      },
      "semiquantitation": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "category",
      "finding",
      "presence"
    ],
    "type": "object"
  },
  "HistoryBudget": {
    "additionalProperties": false,
    "properties": {
      "max_rows": {
        "maximum": 4096,
        "minimum": 1,
        "type": "integer"
      },
      "max_payload_bytes": {
        "maximum": 16777216,
        "minimum": 1,
        "type": "integer"
      }
    },
    "type": "object"
  },
  "IdentityVerification": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "enum": [
          "verified",
          "unresolved"
        ],
        "type": "string"
      },
      "method": {
        "minLength": 1,
        "type": "string"
      },
      "verifier": {
        "minLength": 1,
        "type": "string"
      },
      "assessed_at": {
        "format": "date-time",
        "type": "string"
      },
      "source": {
        "$ref": "#/$defs/Source"
      },
      "ambiguity": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "status",
      "method",
      "verifier",
      "assessed_at",
      "source"
    ],
    "type": "object"
  },
  "IngestionMetadata": {
    "additionalProperties": false,
    "properties": {
      "repository_id": {
        "format": "uuid",
        "type": "string"
      },
      "ingestion_sequence": {
        "exclusiveMinimum": 0,
        "type": "integer"
      },
      "ingested_at": {
        "format": "date-time",
        "type": "string"
      },
      "payload_version": {
        "const": 1,
        "type": "integer"
      }
    },
    "required": [
      "repository_id",
      "ingestion_sequence",
      "ingested_at"
    ],
    "type": "object"
  },
  "IsolateGroup": {
    "additionalProperties": false,
    "properties": {
      "isolate": {
        "$ref": "#/$defs/Reference"
      },
      "susceptibilities": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      },
      "resistance_findings": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      }
    },
    "required": [
      "isolate"
    ],
    "type": "object"
  },
  "IsolateIdentification": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_isolate",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "isolate_identifier": {
        "$ref": "#/$defs/SourceCode"
      },
      "organism": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "identification_state": {
        "enum": [
          "provisional",
          "final",
          "unresolved"
        ],
        "type": "string"
      },
      "method": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "identified": {
        "$ref": "#/$defs/RecordedTime"
      },
      "quantity": {
        "anyOf": [
          {
            "$ref": "#/$defs/NonnegativeQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "semiquantitation": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "isolate_identifier",
      "organism",
      "identification_state"
    ],
    "type": "object"
  },
  "LineageEdge": {
    "additionalProperties": false,
    "properties": {
      "target": {
        "$ref": "#/$defs/Reference"
      },
      "relationship": {
        "enum": [
          "copied_from",
          "derived_from",
          "calculated_from",
          "independent_confirmation",
          "fulfills_order"
        ],
        "type": "string"
      },
      "basis": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "type": "array"
      },
      "rationale": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "target",
      "relationship"
    ],
    "type": "object"
  },
  "MappingIssueV2": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/Reference"
      },
      "reason": {
        "enum": [
          "unsupported_source_structure",
          "specimen_mapped_organism_unavailable",
          "susceptibility_incomplete",
          "unknown_isolate_binding",
          "ambiguous_isolate_binding",
          "missing_collection_time",
          "missing_administration_time",
          "unsupported_antimicrobial_identity",
          "unknown_mapping",
          "binding_target_unavailable",
          "bounded_result_limit_exceeded"
        ],
        "type": "string"
      }
    },
    "required": [
      "reference",
      "reason"
    ],
    "type": "object"
  },
  "MicrobiologyView": {
    "additionalProperties": false,
    "properties": {
      "references": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 512,
        "type": "array"
      },
      "specimens": {
        "items": {
          "$ref": "#/$defs/SpecimenGroup"
        },
        "maxItems": 128,
        "type": "array"
      },
      "isolates": {
        "items": {
          "$ref": "#/$defs/IsolateGroup"
        },
        "maxItems": 256,
        "type": "array"
      },
      "panels": {
        "items": {
          "$ref": "#/$defs/MolecularPanelGroup"
        },
        "maxItems": 64,
        "type": "array"
      }
    },
    "type": "object"
  },
  "MinimumInhibitoryConcentration": {
    "additionalProperties": false,
    "properties": {
      "comparator": {
        "enum": [
          "<",
          "<=",
          "=",
          ">=",
          ">"
        ],
        "type": "string"
      },
      "quantity": {
        "$ref": "#/$defs/NonnegativeQuantity"
      }
    },
    "required": [
      "comparator",
      "quantity"
    ],
    "type": "object"
  },
  "MolecularPanelGroup": {
    "additionalProperties": false,
    "properties": {
      "panel": {
        "$ref": "#/$defs/SourceCode"
      },
      "targets": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "minItems": 1,
        "type": "array"
      }
    },
    "required": [
      "panel",
      "targets"
    ],
    "type": "object"
  },
  "MolecularResult": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_molecular",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "test_identifier": {
        "$ref": "#/$defs/SourceCode"
      },
      "panel_identifier": {
        "anyOf": [
          {
            "$ref": "#/$defs/SourceCode"
          },
          {
            "type": "null"
          }
        ]
      },
      "target": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "result": {
        "enum": [
          "positive",
          "negative",
          "indeterminate",
          "not_performed"
        ],
        "type": "string"
      },
      "method": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "test_identifier",
      "target",
      "result"
    ],
    "type": "object"
  },
  "NonnegativeQuantity": {
    "additionalProperties": false,
    "properties": {
      "value": {
        "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
        "type": "string"
      },
      "unit": {
        "$ref": "#/$defs/Unit"
      }
    },
    "required": [
      "value",
      "unit"
    ],
    "type": "object"
  },
  "PatientStateAssemblyResultV2": {
    "additionalProperties": false,
    "properties": {
      "request": {
        "$ref": "#/$defs/AssemblyRequestV2"
      },
      "snapshot": {
        "$ref": "#/$defs/PatientStateSnapshotV2"
      },
      "candidate_rows": {
        "maximum": 4096,
        "minimum": 0,
        "type": "integer"
      },
      "terminal_count": {
        "maximum": 4096,
        "minimum": 0,
        "type": "integer"
      },
      "bindings": {
        "items": {
          "$ref": "#/$defs/BindingOutcomeV2"
        },
        "maxItems": 1024,
        "type": "array"
      },
      "issues": {
        "items": {
          "$ref": "#/$defs/AssemblyIssueV2"
        },
        "maxItems": 512,
        "type": "array"
      }
    },
    "required": [
      "request",
      "snapshot",
      "candidate_rows",
      "terminal_count"
    ],
    "type": "object"
  },
  "PatientStateScopeV2": {
    "additionalProperties": false,
    "properties": {
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "patient_id": {
        "minLength": 1,
        "type": "string"
      },
      "encounter_id": {
        "minLength": 1,
        "type": "string"
      },
      "review_start": {
        "format": "date-time",
        "type": "string"
      },
      "review_end": {
        "format": "date-time",
        "type": "string"
      },
      "repository_cutoff": {
        "$ref": "#/$defs/RepositoryCutoff"
      }
    },
    "required": [
      "patient_id",
      "encounter_id",
      "review_start",
      "review_end",
      "repository_cutoff"
    ],
    "type": "object"
  },
  "PatientStateSnapshotV2": {
    "additionalProperties": false,
    "properties": {
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "scope": {
        "$ref": "#/$defs/PatientStateScopeV2"
      },
      "items": {
        "items": {
          "$ref": "#/$defs/RetainedStateItemV2"
        },
        "maxItems": 512,
        "type": "array"
      },
      "microbiology": {
        "$ref": "#/$defs/MicrobiologyView"
      },
      "antimicrobial": {
        "$ref": "#/$defs/AntimicrobialView"
      },
      "medication_references": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 512,
        "type": "array"
      },
      "coverage": {
        "items": {
          "$ref": "#/$defs/CoverageV2"
        },
        "maxItems": 2,
        "type": "array"
      },
      "issues": {
        "items": {
          "$ref": "#/$defs/MappingIssueV2"
        },
        "maxItems": 512,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      }
    },
    "required": [
      "scope"
    ],
    "type": "object"
  },
  "PositiveQuantity": {
    "additionalProperties": false,
    "properties": {
      "value": {
        "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
        "type": "string"
      },
      "unit": {
        "$ref": "#/$defs/Unit"
      }
    },
    "required": [
      "value",
      "unit"
    ],
    "type": "object"
  },
  "RecordedConcept": {
    "additionalProperties": false,
    "properties": {
      "raw_display": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "coding": {
        "anyOf": [
          {
            "$ref": "#/$defs/SourceCode"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "raw_display"
    ],
    "type": "object"
  },
  "RecordedDose": {
    "additionalProperties": false,
    "properties": {
      "amount": {
        "$ref": "#/$defs/PositiveQuantity"
      },
      "basis": {
        "enum": [
          "per_dose",
          "per_day",
          "per_kg_per_dose",
          "per_kg_per_day",
          "per_m2_per_dose",
          "total_administered",
          "unknown"
        ],
        "type": "string"
      },
      "basis_detail": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "concentration": {
        "anyOf": [
          {
            "$ref": "#/$defs/PositiveQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "volume": {
        "anyOf": [
          {
            "$ref": "#/$defs/PositiveQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "rate": {
        "anyOf": [
          {
            "$ref": "#/$defs/PositiveQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "duration": {
        "anyOf": [
          {
            "$ref": "#/$defs/PositiveQuantity"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "amount",
      "basis"
    ],
    "type": "object"
  },
  "RecordedFrequency": {
    "additionalProperties": false,
    "properties": {
      "occurrences": {
        "exclusiveMinimum": 0,
        "type": "integer"
      },
      "interval": {
        "$ref": "#/$defs/PositiveQuantity"
      }
    },
    "required": [
      "occurrences",
      "interval"
    ],
    "type": "object"
  },
  "RecordedTime": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "enum": [
          "known",
          "missing",
          "unknown",
          "not_recorded"
        ],
        "type": "string"
      },
      "precision": {
        "enum": [
          "instant",
          "day",
          "approximate",
          "bounded",
          "unknown"
        ],
        "type": "string"
      },
      "value": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "lower": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "upper": {
        "anyOf": [
          {
            "format": "date-time",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "uncertainty": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "status"
    ],
    "type": "object"
  },
  "Reference": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "minLength": 1,
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "kind",
      "id",
      "version"
    ],
    "type": "object"
  },
  "ReportState": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "enum": [
          "preliminary",
          "interim",
          "final",
          "withdrawn"
        ],
        "type": "string"
      },
      "change": {
        "enum": [
          "original",
          "amended",
          "corrected",
          "superseded"
        ],
        "type": "string"
      },
      "reported": {
        "$ref": "#/$defs/RecordedTime"
      },
      "available": {
        "$ref": "#/$defs/RecordedTime"
      },
      "preliminary_reported": {
        "$ref": "#/$defs/RecordedTime"
      },
      "final_reported": {
        "$ref": "#/$defs/RecordedTime"
      },
      "changed": {
        "$ref": "#/$defs/RecordedTime"
      }
    },
    "required": [
      "status"
    ],
    "type": "object"
  },
  "RepositoryCutoff": {
    "additionalProperties": false,
    "properties": {
      "repository_id": {
        "format": "uuid",
        "type": "string"
      },
      "fact_watermark": {
        "minimum": 0,
        "type": "integer"
      },
      "captured_at": {
        "format": "date-time",
        "type": "string"
      }
    },
    "required": [
      "repository_id",
      "fact_watermark",
      "captured_at"
    ],
    "type": "object"
  },
  "ResistanceFinding": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_resistance",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "category": {
        "enum": [
          "phenotype",
          "genotype",
          "mechanism",
          "esbl",
          "carbapenemase",
          "inducible_resistance",
          "resistance_gene"
        ],
        "type": "string"
      },
      "target": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "method": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "result": {
        "enum": [
          "positive",
          "negative",
          "indeterminate",
          "not_performed"
        ],
        "type": "string"
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "category",
      "target",
      "result"
    ],
    "type": "object"
  },
  "RetainedStateItemV2": {
    "additionalProperties": false,
    "properties": {
      "fact": {
        "discriminator": {
          "mapping": {
            "antimicrobial_administration": "#/$defs/CompletedAntimicrobialAdministration",
            "antimicrobial_non_delivery": "#/$defs/AntimicrobialNonDelivery",
            "antimicrobial_order": "#/$defs/AntimicrobialOrder",
            "blood_culture_bottle": "#/$defs/BloodCultureBottle",
            "blood_culture_set": "#/$defs/BloodCultureSet",
            "microbiology_culture": "#/$defs/CultureFinding",
            "microbiology_direct_examination": "#/$defs/DirectExamination",
            "microbiology_isolate": "#/$defs/IsolateIdentification",
            "microbiology_molecular": "#/$defs/MolecularResult",
            "microbiology_resistance": "#/$defs/ResistanceFinding",
            "microbiology_specimen": "#/$defs/Specimen",
            "microbiology_susceptibility": "#/$defs/SusceptibilityResult"
          },
          "propertyName": "kind"
        },
        "oneOf": [
          {
            "$ref": "#/$defs/Specimen"
          },
          {
            "$ref": "#/$defs/DirectExamination"
          },
          {
            "$ref": "#/$defs/CultureFinding"
          },
          {
            "$ref": "#/$defs/IsolateIdentification"
          },
          {
            "$ref": "#/$defs/SusceptibilityResult"
          },
          {
            "$ref": "#/$defs/ResistanceFinding"
          },
          {
            "$ref": "#/$defs/MolecularResult"
          },
          {
            "$ref": "#/$defs/BloodCultureSet"
          },
          {
            "$ref": "#/$defs/BloodCultureBottle"
          },
          {
            "$ref": "#/$defs/AntimicrobialOrder"
          },
          {
            "$ref": "#/$defs/CompletedAntimicrobialAdministration"
          },
          {
            "$ref": "#/$defs/AntimicrobialNonDelivery"
          }
        ]
      },
      "expected_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "ingestion": {
        "anyOf": [
          {
            "$ref": "#/$defs/IngestionMetadata"
          },
          {
            "type": "null"
          }
        ]
      },
      "inclusion": {
        "enum": [
          "in_window",
          "contextual_parent",
          "unplaced"
        ],
        "type": "string"
      },
      "contextual_for": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      }
    },
    "required": [
      "fact",
      "expected_digest",
      "inclusion"
    ],
    "type": "object"
  },
  "Source": {
    "additionalProperties": false,
    "properties": {
      "namespace": {
        "minLength": 1,
        "type": "string"
      },
      "identifier": {
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "channel": {
        "enum": [
          "measurement",
          "external_record",
          "clinician",
          "patient",
          "system"
        ],
        "type": "string"
      }
    },
    "required": [
      "namespace",
      "identifier",
      "channel"
    ],
    "type": "object"
  },
  "SourceCode": {
    "additionalProperties": false,
    "properties": {
      "namespace": {
        "minLength": 1,
        "type": "string"
      },
      "code": {
        "minLength": 1,
        "type": "string"
      },
      "version": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "raw_display": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "namespace",
      "code",
      "raw_display"
    ],
    "type": "object"
  },
  "Specimen": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_specimen",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "accession": {
        "$ref": "#/$defs/SourceCode"
      },
      "specimen_type": {
        "$ref": "#/$defs/RecordedConcept"
      },
      "site": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "collected": {
        "$ref": "#/$defs/RecordedTime"
      },
      "received": {
        "$ref": "#/$defs/RecordedTime"
      },
      "collector": {
        "anyOf": [
          {
            "maxLength": 4096,
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "recorded_adequacy": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "accession",
      "specimen_type"
    ],
    "type": "object"
  },
  "SpecimenGroup": {
    "additionalProperties": false,
    "properties": {
      "specimen": {
        "$ref": "#/$defs/Reference"
      },
      "examinations": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      },
      "cultures": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      },
      "isolates": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      },
      "molecular_results": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "maxItems": 64,
        "type": "array"
      }
    },
    "required": [
      "specimen"
    ],
    "type": "object"
  },
  "StableIdentity": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "minLength": 1,
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "kind",
      "id"
    ],
    "type": "object"
  },
  "SusceptibilityInterpretation": {
    "additionalProperties": false,
    "properties": {
      "raw": {
        "maxLength": 4096,
        "minLength": 1,
        "type": "string"
      },
      "coding": {
        "anyOf": [
          {
            "$ref": "#/$defs/SourceCode"
          },
          {
            "type": "null"
          }
        ]
      },
      "category": {
        "enum": [
          "susceptible",
          "intermediate",
          "resistant",
          "other",
          "unknown"
        ],
        "type": "string"
      },
      "meaning_limitation": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "raw",
      "category"
    ],
    "type": "object"
  },
  "SusceptibilityResult": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "microbiology_susceptibility",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "enum": [
          "observed",
          "reported"
        ],
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/BoundedProvenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "contract_version": {
        "const": "2",
        "type": "string"
      },
      "source_identifiers": {
        "items": {
          "$ref": "#/$defs/SourceCode"
        },
        "maxItems": 16,
        "type": "array"
      },
      "domain_bindings": {
        "items": {
          "$ref": "#/$defs/DomainBinding"
        },
        "maxItems": 16,
        "type": "array"
      },
      "disclosures": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "maxItems": 32,
        "type": "array"
      },
      "report": {
        "$ref": "#/$defs/ReportState"
      },
      "test_identifier": {
        "$ref": "#/$defs/SourceCode"
      },
      "antimicrobial": {
        "$ref": "#/$defs/AntimicrobialIdentity"
      },
      "mic": {
        "anyOf": [
          {
            "$ref": "#/$defs/MinimumInhibitoryConcentration"
          },
          {
            "type": "null"
          }
        ]
      },
      "zone_diameter": {
        "anyOf": [
          {
            "$ref": "#/$defs/NonnegativeQuantity"
          },
          {
            "type": "null"
          }
        ]
      },
      "interpretation": {
        "anyOf": [
          {
            "$ref": "#/$defs/SusceptibilityInterpretation"
          },
          {
            "type": "null"
          }
        ]
      },
      "result_status": {
        "enum": [
          "reported",
          "indeterminate",
          "not_performed"
        ],
        "type": "string"
      },
      "method": {
        "anyOf": [
          {
            "$ref": "#/$defs/RecordedConcept"
          },
          {
            "type": "null"
          }
        ]
      },
      "breakpoint": {
        "anyOf": [
          {
            "$ref": "#/$defs/BreakpointContext"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "origin",
      "provenance",
      "time",
      "temporal_status",
      "report",
      "test_identifier",
      "antimicrobial",
      "result_status"
    ],
    "type": "object"
  },
  "Unit": {
    "additionalProperties": false,
    "properties": {
      "raw": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "status": {
        "enum": [
          "unresolved",
          "assessed",
          "normalized"
        ],
        "type": "string"
      },
      "system": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "code": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "limitation": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "status"
    ],
    "type": "object"
  },
  "MicroStateResponse": {
    "additionalProperties": false,
    "properties": {
      "transport_version": {
        "const": "1",
        "type": "string"
      },
      "assembly": {
        "$ref": "#/$defs/PatientStateAssemblyResultV2"
      },
      "state_context": {
        "maxLength": 65536,
        "minLength": 1,
        "pattern": "^[A-Za-z0-9_.=-]+$",
        "type": "string"
      }
    },
    "required": [
      "assembly",
      "state_context"
    ],
    "type": "object"
  },
  "ClinicalInference": {
    "additionalProperties": false,
    "properties": {
      "kind": {
        "const": "inference",
        "type": "string"
      },
      "id": {
        "minLength": 1,
        "type": "string"
      },
      "revision": {
        "minLength": 1,
        "type": "string"
      },
      "binding": {
        "$ref": "#/$defs/Binding"
      },
      "origin": {
        "const": "inferred",
        "type": "string"
      },
      "provenance": {
        "$ref": "#/$defs/Provenance"
      },
      "time": {
        "$ref": "#/$defs/ClinicalTime"
      },
      "verification": {
        "enum": [
          "unverified",
          "verified",
          "clinician_confirmed"
        ],
        "type": "string"
      },
      "conflict": {
        "enum": [
          "none_known",
          "unresolved",
          "resolved",
          "unknown"
        ],
        "type": "string"
      },
      "temporal_status": {
        "enum": [
          "current",
          "historical",
          "unknown"
        ],
        "type": "string"
      },
      "uncertainty": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      },
      "supersedes": {
        "anyOf": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "type": "null"
          }
        ]
      },
      "correction_reason": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "statement": {
        "minLength": 1,
        "type": "string"
      },
      "inputs": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "minItems": 1,
        "type": "array"
      },
      "method": {
        "$ref": "#/$defs/Reference"
      },
      "applicability": {
        "minLength": 1,
        "type": "string"
      },
      "validation_references": {
        "items": {
          "$ref": "#/$defs/Reference"
        },
        "type": "array"
      },
      "validation_limitations": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "target": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "horizon": {
        "anyOf": [
          {
            "minLength": 1,
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "id",
      "revision",
      "binding",
      "provenance",
      "time",
      "temporal_status",
      "statement",
      "inputs",
      "method",
      "applicability"
    ],
    "type": "object"
  },
  "Provenance": {
    "additionalProperties": false,
    "properties": {
      "source": {
        "$ref": "#/$defs/Source"
      },
      "actor": {
        "minLength": 1,
        "type": "string"
      },
      "recorded_at": {
        "format": "date-time",
        "type": "string"
      },
      "upstream": {
        "items": {
          "$ref": "#/$defs/LineageEdge"
        },
        "type": "array"
      },
      "lineage": {
        "enum": [
          "complete",
          "incomplete",
          "unknown"
        ],
        "type": "string"
      },
      "limitations": {
        "items": {
          "minLength": 1,
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "source",
      "actor",
      "recorded_at",
      "lineage"
    ],
    "type": "object"
  },
  "MicroPreparedResponse": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "const": "prepared",
        "type": "string"
      },
      "execution_id": {
        "format": "uuid",
        "type": "string"
      },
      "inference": {
        "$ref": "#/$defs/ClinicalInference"
      },
      "command": {
        "maxLength": 65536,
        "minLength": 1,
        "pattern": "^[A-Za-z0-9_.=-]+$",
        "type": "string"
      }
    },
    "required": [
      "execution_id",
      "inference",
      "command"
    ],
    "type": "object"
  },
  "MicroAntimicrobialEvidenceWitness": {
    "additionalProperties": false,
    "properties": {
      "role": {
        "enum": [
          "S",
          "I",
          "U",
          "D"
        ],
        "type": "string"
      },
      "consumed": {
        "$ref": "#/$defs/Reference"
      },
      "item_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "source_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "original_ingestion": {
        "$ref": "#/$defs/IngestionMetadata"
      },
      "terminal": {
        "$ref": "#/$defs/Reference"
      },
      "terminal_source_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "terminal_ingestion": {
        "$ref": "#/$defs/IngestionMetadata"
      },
      "suitability": {
        "enum": [
          "established",
          "failed",
          "unavailable"
        ],
        "type": "string"
      }
    },
    "required": [
      "role",
      "consumed",
      "item_digest",
      "source_digest",
      "original_ingestion",
      "terminal",
      "terminal_source_digest",
      "terminal_ingestion",
      "suitability"
    ],
    "type": "object"
  },
  "MicroAntimicrobialFinalRecheck": {
    "additionalProperties": false,
    "properties": {
      "scope": {
        "$ref": "#/$defs/PatientStateScopeV2"
      },
      "inference_cutoff": {
        "$ref": "#/$defs/RepositoryCutoff"
      },
      "final_cutoff": {
        "$ref": "#/$defs/RepositoryCutoff"
      },
      "evidence": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/MicroAntimicrobialEvidenceWitness"
          },
          {
            "$ref": "#/$defs/MicroAntimicrobialEvidenceWitness"
          },
          {
            "$ref": "#/$defs/MicroAntimicrobialEvidenceWitness"
          },
          {
            "$ref": "#/$defs/MicroAntimicrobialEvidenceWitness"
          }
        ],
        "type": "array"
      },
      "terminal_facts": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/Specimen"
          },
          {
            "$ref": "#/$defs/IsolateIdentification"
          },
          {
            "$ref": "#/$defs/SusceptibilityResult"
          },
          {
            "$ref": "#/$defs/CompletedAntimicrobialAdministration"
          }
        ],
        "type": "array"
      },
      "inference": {
        "$ref": "#/$defs/MicroAntimicrobialInferenceWitness"
      },
      "policy": {
        "$ref": "#/$defs/Reference"
      },
      "implementation": {
        "$ref": "#/$defs/Reference"
      }
    },
    "required": [
      "scope",
      "inference_cutoff",
      "final_cutoff",
      "evidence",
      "terminal_facts",
      "inference"
    ],
    "type": "object"
  },
  "MicroAntimicrobialInferenceWitness": {
    "additionalProperties": false,
    "properties": {
      "reference": {
        "$ref": "#/$defs/Reference"
      },
      "expected_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "observed_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "ingestion": {
        "$ref": "#/$defs/IngestionMetadata"
      },
      "terminal": {
        "$ref": "#/$defs/Reference"
      },
      "terminal_digest": {
        "pattern": "^[0-9a-f]{64}$",
        "type": "string"
      },
      "terminal_ingestion": {
        "$ref": "#/$defs/IngestionMetadata"
      },
      "method": {
        "$ref": "#/$defs/Reference"
      },
      "inputs": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          }
        ],
        "type": "array"
      },
      "dependencies": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          },
          {
            "$ref": "#/$defs/Reference"
          }
        ],
        "type": "array"
      },
      "declarations": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/LineageEdge"
          },
          {
            "$ref": "#/$defs/LineageEdge"
          },
          {
            "$ref": "#/$defs/LineageEdge"
          },
          {
            "$ref": "#/$defs/LineageEdge"
          }
        ],
        "type": "array"
      },
      "reconstruction_digest": {
        "anyOf": [
          {
            "pattern": "^[0-9a-f]{64}$",
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "reference",
      "expected_digest",
      "observed_digest",
      "ingestion",
      "terminal",
      "terminal_digest",
      "terminal_ingestion",
      "method",
      "inputs",
      "dependencies",
      "declarations",
      "reconstruction_digest"
    ],
    "type": "object"
  },
  "MicroProvenance": {
    "additionalProperties": false,
    "properties": {
      "inference": {
        "$ref": "#/$defs/ClinicalInference"
      },
      "consumed": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "$ref": "#/$defs/RetainedStateItemV2"
          },
          {
            "$ref": "#/$defs/RetainedStateItemV2"
          },
          {
            "$ref": "#/$defs/RetainedStateItemV2"
          },
          {
            "$ref": "#/$defs/RetainedStateItemV2"
          }
        ],
        "type": "array"
      },
      "original_cutoff": {
        "$ref": "#/$defs/RepositoryCutoff"
      },
      "inference_cutoff": {
        "$ref": "#/$defs/RepositoryCutoff"
      },
      "final_recheck": {
        "$ref": "#/$defs/MicroAntimicrobialFinalRecheck"
      },
      "specimen_binding_matches": {
        "type": "boolean"
      },
      "isolate_binding_matches": {
        "type": "boolean"
      },
      "antimicrobial_identity_matches": {
        "type": "boolean"
      },
      "governance_policy": {
        "$ref": "#/$defs/ExactReference"
      },
      "witness_statuses": {
        "maxItems": 4,
        "minItems": 4,
        "prefixItems": [
          {
            "enum": [
              "current",
              "superseded"
            ],
            "type": "string"
          },
          {
            "enum": [
              "current",
              "superseded"
            ],
            "type": "string"
          },
          {
            "enum": [
              "current",
              "superseded"
            ],
            "type": "string"
          },
          {
            "enum": [
              "current",
              "superseded"
            ],
            "type": "string"
          }
        ],
        "type": "array"
      },
      "recheck_reasons": {
        "items": {
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "inference",
      "consumed",
      "original_cutoff",
      "inference_cutoff",
      "final_recheck",
      "specimen_binding_matches",
      "isolate_binding_matches",
      "antimicrobial_identity_matches",
      "governance_policy",
      "witness_statuses",
      "recheck_reasons"
    ],
    "type": "object"
  },
  "MicroExecutionResponse": {
    "additionalProperties": false,
    "properties": {
      "transport_version": {
        "const": "1",
        "type": "string"
      },
      "execution_id": {
        "format": "uuid",
        "type": "string"
      },
      "status": {
        "const": "completed",
        "type": "string"
      },
      "statement": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ]
      },
      "finalized_at": {
        "format": "date-time",
        "type": "string"
      },
      "ingested_at": {
        "format": "date-time",
        "type": "string"
      },
      "governance": {
        "$ref": "#/$defs/GovernanceView"
      },
      "provenance": {
        "$ref": "#/$defs/MicroProvenance"
      }
    },
    "required": [
      "execution_id",
      "statement",
      "finalized_at",
      "ingested_at",
      "governance",
      "provenance"
    ],
    "type": "object"
  },
  "MicroReconciliationResponse": {
    "additionalProperties": false,
    "properties": {
      "status": {
        "enum": [
          "committed_match",
          "absent"
        ],
        "type": "string"
      },
      "execution": {
        "anyOf": [
          {
            "$ref": "#/$defs/MicroExecutionResponse"
          },
          {
            "type": "null"
          }
        ]
      }
    },
    "required": [
      "status",
      "execution"
    ],
    "type": "object"
  }
} as const satisfies Record<string, Schema>;
