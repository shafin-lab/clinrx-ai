import type {CirculatoryState} from '../api/circulatoryTypes';
import type {BedsideScope} from '../hemodynamics/bedsideModel';
import {InfectionLibrary} from '../infectionLibrary/InfectionLibrary';

// Preserve the workspace integration contract. Browsing never consumes or writes clinical records.
export function AntibioticReferences({requested,loading,retrievalError}: {requested:BedsideScope;state?:CirculatoryState;loading:boolean;retrievalError?:string;onKidney:()=>void}){
 return <InfectionLibrary patient={requested.patient} encounter={requested.encounter} unconfirmed={loading||!!retrievalError}/>;
}
