import {useState} from 'react';
import {ComprehensiveDemo} from './demo/ComprehensiveDemo';
import { CirculatoryClient } from './api/circulatoryClient';
import { CirculatoryReview } from './patient/CirculatoryReview';
import { MicroReviewClient } from './api/microClient';
import { ReviewClient } from './api/client';
import { demo } from './config';
import { PatientReviewPage } from './patient/PatientReviewPage';
export default function App() {
  const [clients]=useState(()=>{try{return {circulatory:new CirculatoryClient(demo.base,demo.patient,demo.encounter),patient:new ReviewClient(demo.base,demo.patient,demo.encounter),micro:new MicroReviewClient(demo.base,demo.patient,demo.encounter)};}catch{return null;}});
  if(!clients)return <main><h1>ClinRx AI</h1><p role="alert">Configure a loopback API origin before opening this synthetic demo.</p></main>;
  if(new URLSearchParams(window.location.search).get('workspace')==='legacy')return <><PatientReviewPage client={clients.patient} config={demo} microClient={clients.micro}/><div className="m7-shell"><CirculatoryReview client={clients.circulatory} config={demo}/></div></>;
  return <ComprehensiveDemo client={clients.circulatory} config={demo}/>;
}
