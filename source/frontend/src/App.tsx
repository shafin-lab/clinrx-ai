import {useState} from 'react';
import {ComprehensiveDemo} from './demo/ComprehensiveDemo';
import { CirculatoryClient } from './api/circulatoryClient';
import { CirculatoryReview } from './patient/CirculatoryReview';
import { MicroReviewClient } from './api/microClient';
import { ReviewClient } from './api/client';
import { demo, hostedSyntheticDemo } from './config';
import { PatientReviewPage } from './patient/PatientReviewPage';
export default function App() {
  const [clients]=useState(()=>{try{return {circulatory:new CirculatoryClient(demo.base,demo.patient,demo.encounter,fetch,30_000,hostedSyntheticDemo?'same-origin-read-only':'loopback'),patient:new ReviewClient(demo.base,demo.patient,demo.encounter,fetch,30_000,hostedSyntheticDemo?'same-origin-read-only':'loopback'),micro:new MicroReviewClient(demo.base,demo.patient,demo.encounter,fetch,30_000,hostedSyntheticDemo?'same-origin-read-only':'loopback')};}catch{return null;}});
  if(!clients)return <main><h1>ClinRx AI</h1><p role="alert">The synthetic demo connection is unavailable.</p></main>;
  if(hostedSyntheticDemo && new URLSearchParams(window.location.search).get('workspace')==='legacy')return <main><h1>Read-only synthetic demo</h1><p>The legacy workspace is unavailable in this hosted preview.</p><a href="/">Open the comprehensive demo</a></main>;
  if(new URLSearchParams(window.location.search).get('workspace')==='legacy')return <><PatientReviewPage client={clients.patient} config={demo} microClient={clients.micro}/><div className="m7-shell"><CirculatoryReview client={clients.circulatory} config={demo}/></div></>;
  return <ComprehensiveDemo client={clients.circulatory} config={demo}/>;
}
