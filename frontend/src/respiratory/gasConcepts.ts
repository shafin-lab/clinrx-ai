import type {RespiratoryContext} from './respiratoryTypes';

/** Source concepts follow specimen identity; absent mappings never borrow another specimen. */
export function sampleGasConcepts(type:RespiratoryContext['sample_type']){
 const venous={co2:'venous_pco2',oxygen:'pvo2'};
 switch(type){
  case 'arterial':return {co2:'paco2',oxygen:'pao2',saturation:'sao2'};
  case 'central_venous':return {...venous,saturation:'scvo2'};
  case 'mixed_venous':return {...venous,saturation:'svo2'};
  case 'peripheral_venous':return {...venous,saturation:'peripheral_venous_saturation'};
  case 'capillary':return {co2:'capillary_pco2',oxygen:'capillary_po2',saturation:'capillary_saturation'};
  default:return {co2:null,oxygen:null,saturation:null};
 }
}
