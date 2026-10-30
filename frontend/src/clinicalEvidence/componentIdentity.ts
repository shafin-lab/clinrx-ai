import type {Evidence} from '../api/rf2Client';

/** Exact source identity plus source component; equal result values never merge sources. */
export function componentIdentity(e:Evidence,component:string):string{return JSON.stringify([e.repository,e.fact.kind,e.fact.id,e.fact.revision,component]);}
