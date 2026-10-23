import type {M10Snapshot} from './types';
import {productLabel} from './model';

export const commonProducts = [
 ['prbc','PRBC'], ['ffp','Fresh frozen plasma (FFP)'], ['platelets_rdp','RDP'],
 ['platelets_sdp','SDP'], ['cryo','Cryoprecipitate'], ['pcc','PCC'],
 ['fibrinogen_concentrate','Human fibrinogen concentrate'],
] as const;

export function receivedProductName(product:Record<string,any>):string {
 const key=product.preparation;
 return commonProducts.find(([id])=>id===key)?.[1]
  ?? commonProducts.find(([id])=>id===product.family||id==='cryo'&&product.family==='cryoprecipitate')?.[1]
  ?? productLabel(key??product.family??'other');
}

export function ProductReceived({snapshot,disabled,onRecord}:{snapshot?:M10Snapshot;disabled:boolean;onRecord:(product:string)=>void}) {
 const groups:any[]=snapshot?.totals.groups??[];
 const belongs=(g:any,id:string)=>g.preparation===id||(id==='prbc'||id==='pcc'||id==='fibrinogen_concentrate')&&g.family===id||id==='cryo'&&g.family==='cryoprecipitate';
 const other=groups.filter(g=>!commonProducts.some(([id])=>belongs(g,id)));
 return <section className="m10-product-ledger" aria-label="Products received by type">
  <h3>Products received</h3>
  <p>Record each administration separately, or enter a source-reported total with its documented period and detail. Add as many transfusions as needed. Processing options belong to each administration.</p>
  <div className="m10-table-wrap"><table><caption>Received products by type</caption><thead><tr><th>Product</th><th>Known quantities in this period</th><th>Record an administration</th></tr></thead><tbody>
   {commonProducts.map(([id,label])=>{
    const amounts=groups.filter(g=>belongs(g,id));
    return <tr key={id}><th scope="row">{label}</th><td>{amounts.length?amounts.map((g,n)=><div key={n}><strong>{g.known_subtotal} {g.unit}</strong><small>{g.dimension} · {g.basis}</small></div>):<span className="m10-unreported">Not documented</span>}</td><td><button type="button" disabled={disabled} onClick={()=>onRecord(id)}>Record {label}</button></td></tr>;
   })}
   {other.map((g,n)=><tr key={'other'+n}><th scope="row">{productLabel(g.preparation??g.family)}</th><td><strong>{g.known_subtotal} {g.unit}</strong><small>{g.dimension} · {g.basis}</small></td><td>Use Record product or event</td></tr>)}
  </tbody></table></div>
  <p><small>Not documented does not mean zero received. Units, platelet pools, actual mL, PCC IU and fibrinogen grams retain separate source bases. PCC and fibrinogen are not converted to FFP or cryoprecipitate units.</small></p>
 </section>;
}
