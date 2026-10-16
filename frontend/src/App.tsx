import { CirculatoryClient } from './api/circulatoryClient';
import { CirculatoryReview } from './patient/CirculatoryReview';
import { MicroReviewClient } from './api/microClient';
import { ReviewClient } from './api/client';
import { demo } from './config';
import { PatientReviewPage } from './patient/PatientReviewPage';
export default function App() {
  try { return <><PatientReviewPage client={new ReviewClient(demo.base,demo.patient,demo.encounter)} config={demo} microClient={new MicroReviewClient(demo.base,demo.patient,demo.encounter)}/><div className="m7-shell"><CirculatoryReview client={new CirculatoryClient(demo.base,demo.patient,demo.encounter)} config={demo}/></div></>; }
  catch { return <main><h1>ClinRx AI</h1><p role="alert">Configure a loopback API origin before opening this synthetic demo.</p></main>; }
}
