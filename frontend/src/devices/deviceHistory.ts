import {useEffect, useState} from 'react';
import type {ExactRef} from '../api/circulatoryTypes';
import {readRF2JSON} from '../api/rf2JSON';

export const deviceHistoryRoute = '/api/v1/patients/synthetic-p1/encounters/synthetic-e1/synthetic-rf2/devices';

type Context = {patient_id: string; encounter_id: string};
type Source = {namespace: string; identifier: string; version: string | null};
export type RecordedTime = {value: string | null; lower: string | null; upper: string | null; precision: string};
type Episode = {
  reference: ExactRef; context: Context; source: Source; device_type: string; site: string | null;
  laterality: string | null; indication: string | null; status: string;
  inserted: RecordedTime; removed: RecordedTime; replaces: ExactRef | null;
};
type Procedure = {
  reference: ExactRef; context: Context; source: Source; title: string; status: string;
  occurred: RecordedTime; author: string | null; method: string | null; site: string | null;
  complications: string | null; follow_up: string | null; devices: ExactRef[]; reports: ExactRef[];
};
type Output = {context: Context; output: ExactRef; device: ExactRef | null};
export type DeviceHistory = {episodes: Episode[]; procedures: Procedure[]; outputs: Output[]};
export type DeviceState = {status: 'loading'} | {status: 'error'} | {status: 'ready'; history: DeviceHistory};

export function useDeviceHistory(enabled: boolean, patient: string, encounter: string): DeviceState {
  const [state, setState] = useState<DeviceState>({status: 'loading'});
  useEffect(() => {
    if (!enabled) return;
    const abort = new AbortController();
    const timer = window.setTimeout(() => {
      abort.abort();
      setState({status: 'error'});
    }, 15000);
    setState({status: 'loading'});
    async function load() {
      try {
        const response = await fetch(deviceHistoryRoute, {
          signal: abort.signal, cache: 'no-store', credentials: 'same-origin', redirect: 'error',
        });
        if (!response.ok) throw Error('Device history unavailable');
        const history = await readRF2JSON(response) as DeviceHistory;
        const sections = [history.episodes, history.procedures, history.outputs];
        if (sections.some(section => !Array.isArray(section) || section.some(
          item => item.context?.patient_id !== patient || item.context?.encounter_id !== encounter
        ))) throw Error('Device history context mismatch');
        if (!abort.signal.aborted) setState({status: 'ready', history});
      } catch {
        if (!abort.signal.aborted) setState({status: 'error'});
      } finally {
        window.clearTimeout(timer);
      }
    }
    void load();
    return () => {
      abort.abort();
      window.clearTimeout(timer);
    };
  }, [enabled, patient, encounter]);
  return enabled ? state : {status: 'loading'};
}
