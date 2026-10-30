import {ventilatorModeProfile} from './ventilatorModes';
import type {RespiratorySupportType} from './respiratoryTypes';
export const ventilatorModes=['VC–AC','PC–AC','SIMV–VC','SIMV–PC','SIMV','PSV','CPAP','PRVC','APRV','Other / manufacturer-specific'];
export function supportFields(type:RespiratorySupportType,mode:string|null):string[]{
 const observations=['spo2','respiratory_rate'];
 if(type==='room_air'||type==='unknown')return observations;
 if(['nasal_cannula','simple_mask','reservoir_mask','other'].includes(type))return ['oxygen_flow',...observations];
 if(type==='venturi_mask')return ['oxygen_flow','fio2',...observations];
 if(type==='hfnc')return ['total_gas_flow','fio2','gas_temperature',...observations];
 if(type==='niv')return mode==='CPAP'?['peep','fio2',...observations]:mode==='PSV'?['pressure_support','peep','fio2',...observations]:['ipap','epap','set_respiratory_rate','fio2',...observations];
 const profile=ventilatorModeProfile(mode),base=['fio2','peep'];
 const fields:Record<string,string[]>={vc:['set_tidal_volume','set_respiratory_rate','inspiratory_time','inspiratory_flow'],pc:['inspiratory_pressure','set_respiratory_rate','inspiratory_time'],simv_vc:['set_tidal_volume','set_respiratory_rate','pressure_support'],simv_pc:['inspiratory_pressure','set_respiratory_rate','pressure_support','inspiratory_time'],simv:['set_respiratory_rate','pressure_support'],psv:['pressure_support','trigger_cycle','apnoea_backup'],cpap:['apnoea_backup'],prvc:['set_tidal_volume','set_respiratory_rate','inspiratory_time','pressure_limit'],aprv:['p_high','p_low','t_high','t_low']};
 return [...(profile.id==='aprv'?['fio2']:base),...(profile.id?fields[profile.id]:['device_settings']),...observations];
}
