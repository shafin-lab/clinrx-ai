import {useEffect} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import {usePatientEvidenceState} from '../demo/usePatientEvidenceState';
import {M7BedsideReview} from './M7BedsideReview';
import type {BedsideScope} from './bedsideModel';
export function HemodynamicsPage({client,config}:{client:CirculatoryClient;config:BedsideScope}){
 const shared=usePatientEvidenceState(client,config);
 useEffect(()=>{const original=document.title;document.title='ClinRx AI · Hemodynamic bedside review';return()=>{document.title=original;};},[]);
 return <><a className="m7-skip-link" href="#m7-bedside-main">Skip to hemodynamic review</a><M7BedsideReview client={client} requested={config} state={shared.state} loading={shared.loading} retrievalError={shared.error} onRefresh={shared.refresh}/><nav className="m7-return-links" aria-label="Other patient tools"><a href="?workspace=patient">Return to patient overview</a></nav></>;
}
