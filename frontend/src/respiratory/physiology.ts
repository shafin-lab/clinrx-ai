import {ventilatorModeProfile} from './ventilatorModes';
import {respiratoryExternalInput,type RespiratoryEvaluation} from './respiratoryEvaluation';
import type {PhysiologyResult, RespiratoryMeasurement, RespiratoryRecord} from './respiratoryTypes';

/** Calculation versions describe arithmetic and eligibility, not disease classifications. */
export const RESPIRATORY_PHYSIOLOGY_VERSION='m9-physiology-2026-10-27-v3';
export const RESPIRATORY_METHOD_SOURCES={
 pbw:{version:'ARDSNet FACTT protocol, 2001',url:'https://biolincc.nhlbi.nih.gov/media/studies/factt/Protocol.pdf'},
 oxygenation:{version:'PALICC consensus, 2015, arithmetic only',url:'https://pubmed.ncbi.nlm.nih.gov/25647235/'},
 gasEquation:{version:'ERS gas exchange review, 2014',url:'https://publications.ersnet.org/ers-lookup/tab-link/erj-44-04-1023-t04/514171'},
 mechanics:{version:'AARC patient-ventilator assessment guideline, 2024',url:'https://www.aarc.org/wp-content/uploads/2024/10/patient-ventilator-assessment-aarc-cpg.pdf'},
 mechanicsMeasurement:{version:'Original respiratory-mechanics measurement study, 2020',url:'https://journals.physiology.org/doi/full/10.1152/japplphysiol.00059.2020'},
 albumin:{version:'Figge et al., original study, 1998',url:'https://pubmed.ncbi.nlm.nih.gov/9824071/'},
 acidBase:{version:'Berend et al., physiological assessment, corrected 2014',url:'https://www.nejm.org/doi/10.1056/NEJMra1003327'},
 compensation:{version:'Merck Manual adult acid-base compensation conventional ranges, reviewed 2025',url:'https://www.merckmanuals.com/professional/nephrology/acid-base-regulation-and-disorders/acid-base-disorders'},
 winter:{version:'Albert, Dell and Winters original quantitative study, 1967',url:'https://pubmed.ncbi.nlm.nih.gov/6016545/'},
 deadSpace:{version:'Respiratory Care, measurement methods, 2013',url:'https://rc.rcjournal.com/content/respcare/58/7/1143.full.pdf'},
 oxygenTransport:{version:'NIOSH oxygen transport physiology, 2003',url:'https://www.cdc.gov/niosh/docket/archive/pdfs/NIOSH-008/0008-041003-BerndtssonG_Pres.pdf'},
 lungFunction:{version:'ERS/ATS technical standard, 2022',url:'https://publications.ersnet.org/content/erj/60/1/2101499'},
} as const;

type Dimension='pressure'|'airwayPressure'|'fraction'|'volume'|'rate'|'flow'|'cardiacFlow'|'height'|'mass'|'concentration'|'protein'|'number'|'diffusion';
const conversions:Record<Dimension,Readonly<Record<string,number>>>={
 pressure:{mmHg:1,'mm[Hg]':1,kPa:7.5006157584566},
 airwayPressure:{cmH2O:1,'cm[H2O]':1,kPa:10.197162129779,mmHg:1.3595100263597,'mm[Hg]':1.3595100263597},
 fraction:{'1':1,'%':0.01},volume:{mL:1,L:1000},rate:{'/min':1,'min-1':1,'{breaths}/min':1},
 flow:{'L/s':1,'L/min':1/60,'mL/s':0.001},height:{cm:1,m:100,'[in_i]':2.54},
 cardiacFlow:{'L/min':1,'L/s':60,'mL/min':0.001},
 mass:{kg:1},concentration:{'mmol/L':1,'mEq/L':1},protein:{'g/dL':1,'g/L':0.1},number:{'1':1},
 // Diffusion percent-predicted is allowed only for exactly matching source units.
 diffusion:{'mL/min/mmHg':1,'mL/(min.mm[Hg])':1,'mmol/min/kPa':1},
};
type Role=RespiratoryMeasurement['role'];
interface InputSpec {concept:string;dimension:Dimension;min?:number;max?:number;zero?:boolean;roles?:Role[];methods?:string[]}
const measured:Role[]=['measured'];
const setting:Role[]=['set','measured','reported'];
const anyKnown:Role[]=['set','measured','reported','calculated_by_source'];
const s=(concept:string,dimension:Dimension,extra:Partial<InputSpec>={}):InputSpec=>({concept,dimension,...extra});
const pressure=(concept:string)=>s(concept,'pressure');
const airway=(concept:string,zero=false)=>s(concept,'airwayPressure',{zero});
const volume=(concept:string)=>s(concept,'volume');
const concentration=(concept:string)=>s(concept,'concentration');
const fraction=(concept:string)=>s(concept,'fraction',{max:1});
const fio2=s('fio2','fraction',{min:0.21,max:1,roles:setting});
const saturation=s('spo2','fraction',{max:0.97});
const rr=s('respiratory_rate','rate');
const vt=volume('tidal_volume');
const pbwInputs=[s('height','height',{min:100,max:250}),s('equation_coefficient','mass',{roles:anyKnown,methods:['ardsnet_adult_male','ardsnet_adult_female']})];
const caInputs=[pressure('pao2'),s('sao2','fraction',{max:1,methods:['fractional_cooximetry']}),s('hemoglobin','protein')];
const cvInputs=[pressure('pvo2'),s('svo2','fraction',{max:1,methods:['fractional_cooximetry']}),s('hemoglobin','protein')];
const electrolytes=[concentration('sodium'),concentration('chloride'),concentration('bicarbonate')];
const gasInputs=[fio2,pressure('paco2'),pressure('ambient_pressure'),s('water_vapor_pressure','pressure',{zero:true,roles:setting}),s('respiratory_quotient','number',{min:0.1,max:2,roles:setting})];
const fmt=(n:number)=>String(Number(n.toFixed(3)));

/** Same-record arithmetic, with only strictly resolved missing FiO2 permitted externally. */
export function calculateRespiratoryPhysiology(record:RespiratoryRecord,evaluation?:RespiratoryEvaluation):PhysiologyResult[]{
 const results:PhysiologyResult[]=[];
 const c=record.context;
 const recordFailure=record.record_status!=='recorded'?`Record status ${record.record_status} is not usable.`:
  !['final','corrected','preliminary','interim'].includes(record.report_status)?`Report status ${record.report_status} is not usable.`:
  record.change_state==='superseded'?'This record is superseded. Select the exact applicable revision.':null;
 const pin=`${record.id}@${record.revision}`;
 const scope=`Source ${pin}; sample=${c.sample_type}; population=${c.population}; specimen=${c.specimen_id??'unspecified'}; collected=${record.times.collected.value??record.times.collected.status}; settings_confirmed_at_sample=${c.settings_confirmed_at_sample}; passive=${c.passive}; occlusion_confirmed=${c.occlusion_confirmed}; ventilator_mode=${c.ventilator_mode??'unspecified'}; reference_equation=${c.reference_equation??'unspecified'}`;
 function read(spec:InputSpec):{value?:number;description:string;reason?:string}{
  const local=record.measurements.filter(m=>m.concept===spec.concept);
  const external=spec.concept==='fio2'&&!local.length?evaluation?.inputs.get('fio2'):undefined;
  const matches=external?[external.measurement]:local;
  if(!matches.length&&spec.concept==='fio2'&&evaluation?.issues.length)return {description:'fio2: missing',reason:evaluation.issues.join(' ')};
  if(matches.length!==1)return {description:`${spec.concept}: ${matches.length?'duplicate measurements':'missing'}`,reason:`${spec.concept}: ${matches.length?'duplicate measurements are ambiguous':'required measurement is missing'}.`};
  const m=matches[0];const r=m.result;
  const description=`${spec.concept} (${m.label}): ${r.kind==='numeric'?`${r.comparator}${r.raw_value} ${r.unit?.code??'[no unit]'}`:r.kind==='unavailable'?`unavailable: ${r.reason}`:r.raw_value}; role=${m.role}; quality=${m.quality}; method=${m.method??'unspecified'}; acquisition=${m.acquisition?JSON.stringify(m.acquisition):'unspecified'}${external?'; '+respiratoryExternalInput(external.source,m.concept):''}`;
  const bad=(reason:string)=>({description,reason:`${spec.concept}: ${reason}.`});
  if(m.quality!=='usable')return bad(`quality is ${m.quality}, not explicitly usable`);
  if(!(spec.roles??measured).includes(m.role))return bad(`role ${m.role} is incompatible with this method; requires ${(spec.roles??measured).join('/')}`);
  if(r.kind!=='numeric')return bad('an exact numeric result is required');
  if(r.comparator!=='=')return bad('censored result cannot enter arithmetic');
  if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(r.raw_value.trim()))return bad('not an exact finite decimal number');
  const raw=Number(r.raw_value);if(!Number.isFinite(raw))return bad('number is not finite');
  if(!r.unit||!['UCUM','ucum','http://unitsofmeasure.org'].includes(r.unit.namespace))return bad('an explicit supported UCUM unit namespace is required');
  const factor=conversions[spec.dimension][r.unit.code];if(factor===undefined)return bad(`unit ${r.unit.code} is incompatible or unsupported`);
  const v=raw*factor;if(!Number.isFinite(v))return bad('converted number is not finite');
  if(spec.min!==undefined?v<spec.min:spec.zero?v<0:v<=0)return bad('value is outside the permitted physiologic range');
  if(spec.max!==undefined&&v>spec.max)return bad('value is outside the permitted physiologic range');
  if(spec.methods&&!spec.methods.includes(m.method??''))return bad(`explicit method ${spec.methods.join('/')} is required`);
  return {value:v,description};
 }
 function add(id:string,label:string,unit:string,formula:string,specs:InputSpec[],eligibility:()=>string|null,compute:(v:number[])=>number|string,reason:string){
  const reads=specs.map(read);const failures=reads.flatMap(r=>r.reason?[r.reason]:[]);const gate=recordFailure??eligibility();
  const withheld=gate??(failures.length?failures.join(' '):null);
  const inputs=[scope,...reads.map(r=>r.description)];
  if(withheld){results.push({id,label,unit,formula,value:null,reason:`Withheld: ${withheld}`,inputs});return;}
  const result=compute(reads.map(r=>r.value!));
  if(typeof result==='number'&&!Number.isFinite(result)){results.push({id,label,unit,formula,value:null,reason:'Withheld: inputs are incompatible with this equation or yield a nonfinite result.',inputs});return;}
  results.push({id,label,unit,formula,value:typeof result==='number'?fmt(result):result,reason,inputs});
 }
 const ok=()=>null;
 const arterial=()=>c.sample_type==='arterial'?null:'An explicitly arterial blood sample is required; venous and capillary gases cannot substitute.';
 const adult=()=>c.population==='adult'?null:'This method requires confirmed adult population; child, neonate and unknown populations are not eligible.';
 const arterialAdult=()=>arterial()??adult();
 const sampleSettings=()=>c.settings_confirmed_at_sample===true||evaluation?.inputs.has('fio2')?null:'FiO2/support settings must be explicitly confirmed at the time of the sample/measurement.';
 const arterialSettings=()=>arterial()??sampleSettings();
 const staticConditions=()=>c.passive!==true?'Passive respiratory conditions must be confirmed.':c.occlusion_confirmed!==true?'End-inspiratory and total-PEEP occlusion measurements must be confirmed.':null;
 const dynamicConditions=()=>c.passive!==true?'Passive respiratory conditions must be confirmed for the peak-pressure-based estimate.':c.occlusion_confirmed!==true?'Total-PEEP end-expiratory occlusion measurement must be confirmed.':null;
 const computed='Calculated from explicitly usable source measurements with exact inputs shown; no disease classification or treatment recommendation.';

 add('pf_ratio','PaO2/FiO2 ratio','mmHg','PaO2 [mmHg] / FiO2 [fraction]',[pressure('pao2'),fio2],arterialSettings,([p,f])=>p/f,computed);
 add('sf_ratio','SpO2/FiO2 ratio','1','SpO2 [%] / FiO2 [fraction]; SpO2 <=97%',[saturation,fio2],sampleSettings,([o,f])=>100*o/f,'S/F uses conventional percent-number saturation divided by fractional FiO2. It is a pulse-oximetry surrogate restricted here to SpO2 <=97%; it does not establish arterial PO2 or a diagnosis.');
 add('oxygenation_index','Oxygenation index','1','100 × FiO2 [fraction] × mean airway pressure [cmH2O] / PaO2 [mmHg]',[fio2,airway('mean_airway_pressure'),pressure('pao2')],arterialSettings,([f,p,o])=>100*f*p/o,'Arithmetic oxygenation index only; no age-specific disease or severity classification is applied.');
 add('oxygen_saturation_index','Oxygen saturation index','1','100 × FiO2 [fraction] × mean airway pressure [cmH2O] / SpO2 [%]',[fio2,airway('mean_airway_pressure'),saturation],sampleSettings,([f,p,o])=>f*p/o,'Arithmetic saturation index with SpO2 <=97%; no age-specific disease or severity classification is applied.');

 const channel=record.measurements.find(m=>m.concept==='tidal_volume')?.acquisition?.breath_channel;
 const ventilationChannel=()=>{const v=record.measurements.filter(m=>m.concept==='tidal_volume'),r=record.measurements.filter(m=>m.concept==='respiratory_rate');const a=v[0]?.acquisition,b=r[0]?.acquisition;return v.length===1&&r.length===1&&a&&b&&['total','spontaneous'].includes(a.breath_channel)&&a.breath_channel===b.breath_channel&&a.acquisition_id.trim()&&a.acquisition_id===b.acquisition_id?null:'Measured Vt and rate require the same explicit total or spontaneous breath channel and source acquisition/averaging-period identity.';};
 add('minute_ventilation',`Estimated ${channel==='total'||channel==='spontaneous'?channel+' ':''}minute ventilation`,'L/min','Vt [mL] × respiratory rate [/min] / 1000',[vt,rr],ventilationChannel,([v,r])=>v*r/1000,'Measured tidal volume and rate from this record; does not replace reported ventilator minute ventilation or account for leaks.');
 add('alveolar_ventilation',`Estimated ${channel==='total'||channel==='spontaneous'?channel+' ':''}alveolar ventilation (measured Bohr dead space)`,'L/min','(Vt − measured physiologic dead space) [mL] × rate [/min] / 1000',[vt,s('dead_space_volume','volume',{zero:true,methods:['bohr_volumetric_capnography']}),rr],ventilationChannel,([v,d,r])=>d<=v?(v-d)*r/1000:NaN,'Requires measured physiologic dead space by Bohr volumetric capnography; anatomical dead space and body-weight estimates do not substitute.');
 const pbw=(h:number,b:number)=>{const weight=b+2.3*(h/2.54-60);return weight>0?weight:NaN;};
 const pbwGate=()=>{const population=adult();if(population)return population;const coefficient=record.measurements.filter(m=>m.concept==='equation_coefficient');if(coefficient.length===1){const m=coefficient[0];if(m.result.kind==='numeric'&&((m.method==='ardsnet_adult_male'&&Number(m.result.raw_value)!==50)||(m.method==='ardsnet_adult_female'&&Number(m.result.raw_value)!==45.5)))return 'Named adult equation coefficient does not match 50 kg (male equation) or 45.5 kg (female equation).';}return null;};
 add('predicted_body_weight','Predicted body weight (adult ARDSNet)','kg','Adult named coefficient (50 or 45.5 kg) + 2.3 × (height [inches] − 60)',pbwInputs,pbwGate,([h,b])=>pbw(h,b),'The source explicitly selects the adult sex-specific ARDSNet equation coefficient; actual body weight is not used. Height eligibility is restricted to 100–250 cm.');
 add('tidal_volume_per_pbw','Tidal volume / predicted body weight','mL/kg','Measured Vt [mL] / adult ARDSNet predicted body weight [kg]',[vt,...pbwInputs],pbwGate,([v,h,b])=>v/pbw(h,b),computed);
 add('driving_pressure','Driving pressure (static respiratory system)','cmH2O','Measured plateau pressure − measured total PEEP',[airway('plateau_pressure'),airway('total_peep',true)],staticConditions,([p,e])=>p>e?p-e:NaN,'Static respiratory-system pressure difference; requires passive conditions and confirmed occlusion measurements. Set PEEP and peak pressure cannot substitute.');
 add('static_compliance','Static respiratory-system compliance','mL/cmH2O','Measured Vt / (plateau pressure − total PEEP)',[vt,airway('plateau_pressure'),airway('total_peep',true)],staticConditions,([v,p,e])=>p>e?v/(p-e):NaN,'Respiratory-system compliance includes lung and chest wall; it is not isolated lung compliance.');
 add('dynamic_compliance','Dynamic respiratory-system compliance estimate','mL/cmH2O','Measured Vt / (peak pressure − total PEEP)',[vt,airway('peak_pressure'),airway('total_peep',true)],dynamicConditions,([v,p,e])=>p>e?v/(p-e):NaN,'Peak-pressure-based estimate includes resistive pressure; it does not substitute for static compliance or plateau pressure.');
 add('airway_resistance','Inspiratory resistance estimate','cmH2O·s/L','(Peak pressure − plateau pressure) / constant inspiratory flow [L/s]',[airway('peak_pressure'),airway('plateau_pressure'),s('inspiratory_flow','flow',{methods:['constant_inspiratory_flow']})],()=>staticConditions()??(ventilatorModeProfile(c.ventilator_mode).conventionalVolumeControl?null:'Explicit conventional volume-control mode with constant inspiratory flow is required; adaptive, mixed and unknown modes are not eligible.'),([p,l,f])=>p>=l?(p-l)/f:NaN,'Estimate includes endotracheal tube and respiratory-system resistive effects; requires measured constant flow in passive volume-control conditions.');

 const alveolar=([f,co2,pb,water,r]:number[])=>pb>water?f*(pb-water)-co2*(f+(1-f)/r):NaN;
 add('alveolar_oxygen_pressure','Alveolar oxygen pressure (general gas equation)','mmHg','PAO2 = FiO2 × (PB − PH2O) − PaCO2 × [FiO2 + (1 − FiO2) / RQ]',gasInputs,arterialSettings,v=>{const a=alveolar(v);return a>=0?a:NaN;},'Explicit barometric pressure, water vapour pressure and respiratory quotient are required. Assumes negligible inspired CO2, steady state and alveolar PCO2 approximated by measured arterial PCO2.');
 add('aa_gradient','Alveolar–arterial oxygen gradient','mmHg','A–a = {FiO2 × (PB − PH2O) − PaCO2 × [FiO2 + (1 − FiO2) / RQ]} − PaO2',[...gasInputs,pressure('pao2')],arterialSettings,v=>{const a=alveolar(v.slice(0,5));return a>=0?a-v[5]:NaN;},'Uses the general alveolar gas equation and explicit environmental/RQ inputs; no automatic age-normal range or disease diagnosis. Negative calculated gradients are retained for review of assumptions.');

 const ph=s('ph','number',{min:6,max:8.5});
 add('ph_description','Arterial pH description (adult)','', 'pH <7.35: acidemia; 7.35–7.45: within adult arterial interval; >7.45: alkalemia',[ph],arterialAdult,([p])=>p<7.35?'Acidemia':p>7.45?'Alkalemia':'Within adult arterial pH interval','Describes measured adult arterial pH only; a primary process, mixed disorder or normal acid-base physiology is not established.');
 add('anion_gap','Anion gap (without potassium)','mmol/L','Measured Na − measured Cl − measured bicarbonate',electrolytes,ok,([na,cl,b])=>na-cl-b,'Same-record measured electrolytes only. No potassium term; no universal normal gap is applied. Source-calculated gas bicarbonate cannot silently substitute for measured chemistry.');
 add('albumin_adjusted_anion_gap','Albumin-adjusted anion gap (adult convention)','mmol/L','Na − Cl − bicarbonate + 2.5 × (4 − albumin [g/dL])',[...electrolytes,s('albumin','protein',{zero:true})],adult,([na,cl,b,a])=>na-cl-b+2.5*(4-a),'Figge adjustment with explicitly stated reference albumin 4 g/dL. It is an approximation, not a measured analyte or automatic diagnosis.');
 add('winter_expected_paco2','Conditional Winter expected PaCO2','mmHg','Expected PaCO2 = 1.5 × bicarbonate [mmol/L] + 8 ±2',[s('bicarbonate','concentration',{roles:['measured','calculated_by_source']}),ph,pressure('paco2')],arterialAdult,([b,p])=>b<24&&p<7.35?`${fmt(1.5*b+6)}–${fmt(1.5*b+10)}`:'Not applicable','Conditional interval if metabolic acidosis is the primary process; measured arterial PaCO2 remains source evidence. Does not establish a primary or mixed disorder.');
 const last=results.at(-1)!;if(last.value==='Not applicable'){last.value=null;last.reason='Withheld: Winter compensation is conditional on a primary metabolic acidosis; requires low bicarbonate (<24) with arterial acidemia for this display.';}else if(last.value!==null){const b=read(s('bicarbonate','concentration',{roles:['measured','calculated_by_source']})).value!;const p=read(pressure('paco2')).value!;const low=1.5*b+6;const high=low+4;last.reason+=` Measured arterial PaCO2 ${fmt(p)} mmHg is ${p<low?'below':p>high?'above':'within'} the conditional interval.`;}
 add('respiratory_compensation','Conditional respiratory compensation possibilities','mmol/L','If primary PaCO2 disturbance: HCO3 baseline 24; per +10 mmHg, acute +1–2/chronic +3–4; per −10, acute −1–2/chronic −4–5',[pressure('paco2')],arterialAdult,([p])=>{const d=Math.abs(p-40)/10;return p>40?`If primary respiratory acidosis: acute HCO3 ${fmt(24+d)}–${fmt(24+2*d)}; chronic ${fmt(24+3*d)}–${fmt(24+4*d)}`:p<40?`If primary respiratory alkalosis: acute HCO3 ${fmt(24-2*d)}–${fmt(24-d)}; chronic ${fmt(24-5*d)}–${fmt(24-4*d)}`:'PaCO2 40: no departure from this equation baseline';},'Rule-of-thumb acute and chronic possibilities only; duration and a primary respiratory process are not established by one gas. Values do not establish a diagnosis.');

 const content=([p,sat,hb]:number[])=>1.34*hb*sat+0.003*p;
 add('arterial_oxygen_content','Calculated arterial oxygen content','mL O2/dL','CaO2 = 1.34 × hemoglobin [g/dL] × fractional oxyhaemoglobin FO2Hb [fraction] + 0.003 × PaO2 [mmHg]',caInputs,arterial,content,'Requires explicitly measured fractional oxyhaemoglobin (FO2Hb), expressed relative to total haemoglobin. Functional SaO2, generic co-oximetry saturation, SpO2 and PO2-calculated saturation cannot substitute. Recorded dyshemoglobin fractions are already accounted for in fractional FO2Hb; they are not subtracted twice. Fixed binding and solubility coefficients remain approximations.');
 add('mixed_venous_oxygen_content','Calculated mixed-venous oxygen content','mL O2/dL','CvO2 = 1.34 × hemoglobin [g/dL] × mixed-venous fractional oxyhaemoglobin [fraction] + 0.003 × PvO2 [mmHg]',cvInputs,()=>c.sample_type==='mixed_venous'?null:'An explicitly mixed-venous sample is required; central/peripheral venous saturation is not interchangeable.',content,'Explicitly fractional mixed-venous oxyhaemoglobin only; functional or unspecified saturation is withheld. Same binding and solubility approximations as arterial content.');
 add('oxygen_delivery','Calculated oxygen delivery','mL O2/min','DO2 = [1.34 × Hb × fractional FO2Hb + 0.003 × PaO2] × measured cardiac output [L/min] ×10',[...caInputs,s('cardiac_output','cardiacFlow')],arterial,v=>content(v.slice(0,3))*v[3]*10,'Requires arterial evidence and contemporaneous measured cardiac output documented in this coherent record. No cross-report pairing or indexed delivery is inferred.');
 add('oxygen_extraction_ratio','Oxygen extraction ratio','%','100 × (CaO2 − mixed-venous CvO2) / CaO2',[],()=>'Paired, contemporaneous arterial and mixed-venous samples with exact identities are required. This single-sample record cannot establish that pair; central venous values cannot substitute.',()=>NaN,'');

 const mixed=s('mixed_expired_pco2','pressure',{zero:true,methods:['mixed_expired_collection','volumetric_capnography']});
 add('enghoff_dead_space_fraction','Enghoff dead-space fraction estimate','1','(PaCO2 − mixed-expired PCO2) / PaCO2',[pressure('paco2'),mixed],arterial,([a,e])=>a>=e?(a-e)/a:NaN,'Enghoff substitutes arterial for alveolar PCO2 and includes gas-exchange effects of shunt/V/Q inequality; it is distinct from measured Bohr dead space. End-tidal PCO2 does not substitute for mixed-expired PCO2.');
 add('bohr_dead_space_fraction','Bohr dead-space fraction','1','(Measured alveolar PCO2 − mixed-expired PCO2) / measured alveolar PCO2',[s('alveolar_pco2','pressure',{methods:['volumetric_capnography']}),mixed],ok,([a,e])=>a>=e?(a-e)/a:NaN,'Requires method-specific alveolar and mixed-expired PCO2 measurements; neither arterial nor end-tidal PCO2 is silently substituted. Assumes negligible inspired CO2.');

 add('fev1_fvc_ratio','FEV1/FVC ratio','1','Measured FEV1 [L] / measured FVC [L]',[volume('fev1'),volume('fvc')],ok,([a,b])=>a<=b?a/b:NaN,'Arithmetic from usable same-report forced manoeuvre values. No fixed obstruction threshold or disease diagnosis is applied.');
 for(const concept of ['fev1','fvc','tlc','dlco']){
  const dim:Dimension=concept==='dlco'?'diffusion':'volume';
  add(`${concept}_percent_predicted`,`${concept.toUpperCase()} percent predicted`,'%','100 × measured value / explicitly reported predicted value (matching units)',[s(concept,dim),s(`${concept}_predicted`,dim,{roles:['reported','calculated_by_source']})],()=>{if(!c.reference_equation?.trim())return 'An explicitly named source reference equation is required; no age, sex, height or ancestry is inferred.';if(concept==='dlco'){const a=record.measurements.find(m=>m.concept==='dlco')?.result;const b=record.measurements.find(m=>m.concept==='dlco_predicted')?.result;if(a?.kind==='numeric'&&b?.kind==='numeric'&&a.unit?.code!==b.unit?.code)return 'DLCO measured and predicted compound units must match exactly; no gas-volume convention or approximate compound conversion is assumed.';}return null;},([a,b])=>100*a/b,`Source-supplied prediction only; reference=${c.reference_equation??'missing'}. Percent predicted alone does not define a normal range or diagnose impairment.`);
 }
 for(const [id,label,formula,reason] of [
  ['shunt_fraction','Pulmonary shunt fraction','Qs/Qt = (CcO2 − CaO2) / (CcO2 − mixed-venous CvO2)','Requires exact paired arterial/mixed-venous samples, validated end-capillary oxygen-content assumptions and protocol.'],
  ['transpulmonary_pressure','Transpulmonary pressure','Airway pressure − pleural pressure estimate','Requires calibrated esophageal-pressure measurements, acquisition phase and a validated occlusion protocol.'],
  ['lung_function_z_score','Lung-function z-score','Reference-equation-specific transformation','Requires validated reference-equation implementation, population eligibility and distribution parameters.'],
  ['sleep_indices','Sleep study derived indices','Protocol-specific event counts / validated sleep time','Source sleep scoring rules, event series and valid study duration are not encoded for automatic scoring.'],
  ['extracorporeal_gas_transfer','Extracorporeal gas transfer','Protocol-specific paired gas contents × circuit flow','Requires paired pre/post-membrane gas evidence, circuit flow, sampling times and validated extracorporeal method.'],
 ])add(id,label,'',formula,[],()=>reason,()=>NaN,'');
 return results;
}
