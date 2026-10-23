import {useEffect} from 'react';
import type {CirculatoryClient} from '../api/circulatoryClient';
import {RenalFluidClient} from '../api/renalFluidClient';
import {usePatientEvidenceState} from '../demo/usePatientEvidenceState';
import type {BedsideScope} from '../hemodynamics/bedsideModel';
import {RenalBedsideReview} from './RenalBedsideReview';
export function RenalPage({client,config}:{client:CirculatoryClient;config:BedsideScope}){
 const shared=usePatientEvidenceState(client,config);
 useEffect(()=>{const old=document.title;document.title='ClinRx AI · Renal system';return()=>{document.title=old;};},[]);
 return <><a className="m7-skip-link" href="#m8-bedside-main">Skip to renal review</a><RenalBedsideReview state={shared.renalFluid} catalog={shared.rf2} client={client instanceof RenalFluidClient?client:undefined} requested={config} loading={shared.loading} error={shared.error} onRefresh={shared.refresh}/><nav className="m7-return-links" aria-label="Other patient reviews"><a href="?workspace=patient">Patient overview</a><a href="?workspace=hemodynamics">Cardiovascular system</a></nav></>;
}
