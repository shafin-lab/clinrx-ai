import type {CirculatoryItem} from '../api/circulatoryTypes';
import {record,words} from './evidencePresentation';
/** Source mapping status for each supplied quantity, without inferring applicability. */
export function sourceUnitMappings(item:CirculatoryItem){
 const f=item.fact,a=record(f.action),mode=a.delivery?'Delivered':a.prescribed?'Prescribed':a.prepared?'Prepared':null,d=record(a.delivery??a.prescribed??a.prepared);
 const candidates:[string,unknown][]=[['Result',record(f.result).quantity],['Event amount',f.recorded_amount]];
 if(mode)candidates.push([mode+' rate',d.rate],[mode+' concentration',d.concentration]);
 return candidates.filter(([,q])=>Object.keys(record(q)).length>0).map(([label,q])=>({label,unit:String(record(record(q).unit).raw??'Not recorded'),status:words(record(record(q).unit).status)||'Not supplied'}));
}
