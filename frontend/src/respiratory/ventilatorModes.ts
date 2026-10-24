/** Non-executable source-label semantics. No manufacturer equivalence or setting selection. */
export const VENTILATOR_MODE_VERSION='m9-mode-semantics-2026-10-25-v1';
const profiles={
 vc:{label:'Conventional volume control',hints:['Configured tidal-volume target and rate','Measured delivered volume and total rate','Measured inspiratory flow and waveform'],conventionalVolumeControl:true},
 pc:{label:'Pressure control',hints:['Configured inspiratory pressure and its pressure basis','Configured inspiratory time and rate','Measured delivered volume and rate'],conventionalVolumeControl:false},
 simv_vc:{label:'SIMV with volume-controlled mandatory breaths',hints:['Mandatory volume target and mandatory rate','Spontaneous pressure support if recorded','Separate mandatory, spontaneous and total measured channels'],conventionalVolumeControl:false},
 simv_pc:{label:'SIMV with pressure-controlled mandatory breaths',hints:['Mandatory pressure and inspiratory time','Spontaneous pressure support if recorded','Separate mandatory, spontaneous and total measured channels'],conventionalVolumeControl:false},
 simv:{label:'SIMV · control variable unspecified',hints:['Source control-variable wording','Mandatory rate and spontaneous support','Separate measured breath channels'],conventionalVolumeControl:false},
 psv:{label:'Pressure support ventilation',hints:['Pressure-support level and PEEP','Trigger/cycling wording if recorded','Measured spontaneous volume and rate'],conventionalVolumeControl:false},
 cpap:{label:'Continuous positive airway pressure',hints:['CPAP level','Interface recorded separately','Measured spontaneous volume and rate'],conventionalVolumeControl:false},
 prvc:{label:'Pressure-regulated volume control · adaptive',hints:['Configured volume target and pressure limits','Source adaptive-mode wording','Measured delivered volume kept separate from target'],conventionalVolumeControl:false},
 aprv:{label:'Airway pressure release ventilation',hints:['High and low pressure','High and low time','Separate spontaneous and total measured channels'],conventionalVolumeControl:false},
} as const;
type Profile=keyof typeof profiles;
const aliases:Record<string,Profile>={'volume_control':'vc','vc-ac':'vc','vc-cmv':'vc','vc/ac':'vc','vc/cmv':'vc','pc-ac':'pc','pc/ac':'pc','pc-cmv':'pc','pressure_control':'pc','simv-vc':'simv_vc','vc-simv':'simv_vc','simv (vc)':'simv_vc','simv-pc':'simv_pc','pc-simv':'simv_pc','simv (pc)':'simv_pc','simv':'simv','psv':'psv','cpap':'cpap','prvc':'prvc','aprv':'aprv'};
export function ventilatorModeProfile(raw:string|null){const mode=(raw??'').trim().toLowerCase().replace(/[–—−]/g,'-');const id=Object.hasOwn(aliases,mode)?aliases[mode]:undefined;return {version:VENTILATOR_MODE_VERSION,raw,recognized:!!id,id:id??null,...(id?profiles[id]:{label:'Unknown or custom source mode',hints:['Retain source wording; confirm device-specific semantics separately'],conventionalVolumeControl:false}),executable:false as const};}
