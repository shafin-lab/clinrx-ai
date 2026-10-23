"""Cross-owner acceptance: component families, lifecycle, medicines and fluid reuse."""
from uuid import uuid4
from test_m10_backend import case,catalog,draft,save,post,pin,correction
from app.demo.renal_fluid_entry_gateway import RF2


def test_full_product_lifecycle_and_fluid_reconciliation(case):
    c,_=case;repository=catalog(c)['repository'];deliveries=[]
    rows=[('prbc','prbc','2','units','component units','550'),('plasma','ffp','4','units','FFP units','800'),('plasma','solvent_detergent','1','units','plasma units','200'),('platelets','platelets_rdp','6','units','RDP units','300'),('platelets','platelets_pooled','1','pool','pools','250'),('platelets','platelets_sdp','1','apheresis unit','apheresis units','200'),('cryoprecipitate','cryo','10','units','cryo units','120')]
    for family,preparation,count,unit,basis,volume in rows:
        body=draft(repository)
        body['data'].update(product={'family':family,'preparation':preparation,'label':preparation,'units_per_pool':6 if unit=='pool' else None},amounts=[{'dimension':'count','value':count,'unit':unit,'basis':basis},{'dimension':'volume','value':volume,'unit':'mL','basis':'actual administered'}])
        deliveries.append((body,save(c,body)))
    for family,dose,unit,volume in [('pcc','500','IU','20'),('fibrinogen_concentrate','4','g','200')]:
        body=draft(repository,'haemostatic_medication_course')
        body['data'].update(product={'family':family,'preparation':family,'label':family,'factor_basis':'factor IX' if family=='pcc' else None},amounts=[{'dimension':'dose','value':dose,'unit':unit,'basis':family},{'dimension':'vials','value':'1' if family=='pcc' else '4','unit':'vials','basis':'vials used'},{'dimension':'volume','value':volume,'unit':'mL','basis':'actual administered'}],promote_to_medication=True,replacement_rationale='Recorded concentrate choice, with no FFP/cryo equivalence assumed')
        deliveries.append((body,save(c,body)))
    before=catalog(c);assert len(before['medication_exposures'])==2
    quantified={(g['preparation'],g['dimension']):g for g in before['totals']['groups']}
    assert quantified[('ffp','count')]['known_subtotal']=='4'
    assert quantified[('platelets_rdp','count')]['known_subtotal']=='6'
    assert quantified[('platelets_pooled','count')]['unit']=='pool'
    assert quantified[('platelets_sdp','count')]['unit']=='apheresis unit'
    assert quantified[('pcc','dose')]['known_subtotal']=='500' and quantified[('pcc','dose')]['unit']=='IU'
    assert quantified[('fibrinogen_concentrate','dose')]['known_subtotal']=='4' and quantified[('fibrinogen_concentrate','dose')]['unit']=='g'
    product=deliveries[0][0]['data']['product']
    for kind in ('transfusion_request','transfusion_prescription'):
        save(c,draft(repository,kind,{'title':kind,'product':product,'indication':'Synthetic request only','quantities':[{'dimension':'count','value':'99','unit':'units','basis':'component units'}]}))
    for status in ('allocated','issued','returned','wasted'):
        save(c,draft(repository,'blood_product_disposition',{'title':status,'product':product,'status':status,'quantities':[{'dimension':'count','value':'99','unit':'units','basis':'component units'}]}))
    assert catalog(c)['totals']['groups']==before['totals']['groups']
    # Reuse a true fluid-chart owner; this assertion adds no second blood volume.
    fluid={'repository':repository,'id':str(uuid4()),'revision':str(uuid4()),'actor':'Synthetic nurse','recorded_at':'2026-10-08T09:30:00Z','chart':{'category':'input_blood','amount':'550','unit':'mL','point':'2026-10-08T09:00:00Z','start':'2026-10-08T08:30:00Z','end':'2026-10-08T09:00:00Z','source_context':'Same synthetic PRBC delivery','uncertainty':'Source transcribed','new_collection_reason':'Explicit existing delivery fluid chart owner'},'note':None,'predecessor':None,'reason':None}
    response=c.post(RF2+'/save',json=fluid,headers={'origin':'http://127.0.0.1:5290'});assert response.status_code==200,response.text;f=response.json()['evidence']
    fluid_pin={'reference':{'kind':f['fact']['kind'],'id':f['fact']['id'],'version':f['fact']['revision']},'digest':f['digest']}
    save(c,draft(repository,'fluid_administration_link',{'title':'Same blood volume','administration':pin(deliveries[0][1]),'fluid':fluid_pin,'relationship':'same_delivery','matched_volume_ml':'550'}))
    assert catalog(c)['fluid_reconciliation']['links'][0]['status']=='linked_once'
    save(c,draft(repository,'transfusion_reaction',{'title':'Suspected reaction','implicated':[pin(deliveries[0][1])],'symptoms':'Synthetic itching','actions':'Stopped and reviewed','investigation':'Blood service informed','classification':'Suspected, unconfirmed'}))
    save(c,draft(repository,'haemorrhage_episode',{'title':'Bleeding review','setting':'trauma','bleeding':'yes','major_haemorrhage_protocol':'activated','blood_loss_ml':'1200'}))
    current=catalog(c);assert len(current['totals']['groups'])==len(before['totals']['groups'])
    corrected=correction(deliveries[0][0],deliveries[0][1],amounts=[{'dimension':'volume','value':'275','unit':'mL','basis':'actual administered'}]);save(c,corrected)
    assert catalog(c)['fluid_reconciliation']['links'][0]['status']=='unresolved'
    # The linked original fluid fact is unchanged and no replacement was invented.
    fluid_items=[e for e in catalog(c)['evidence'] if e['fact']['id']==f['fact']['id']]
    assert len(fluid_items)==1 and fluid_items[0]['fact']['revision']==f['fact']['revision']


def test_seven_product_example_and_repeat_transfusion_retain_independent_owners(case):
    c,_=case;repository=catalog(c)['repository']
    inputs=[('prbc','prbc','10','count','units','component units'),('plasma','ffp','10','count','units','component units'),('platelets','platelets_sdp','1','count','units','apheresis units'),('platelets','platelets_rdp','6','count','units','component units'),('cryoprecipitate','cryo','10','count','units','component units'),('pcc','pcc','1000','dose','IU','factor IX'),('fibrinogen_concentrate','fibrinogen_concentrate','2','dose','g','fibrinogen_concentrate')]
    saved=[]
    for family,preparation,value,dimension,unit,basis in inputs:
        body=draft(repository,'haemostatic_medication_course' if dimension=='dose' else 'transfusion_administration')
        body['data'].update(product={'family':family,'preparation':preparation,'label':preparation,'factor_basis':'factor IX' if family=='pcc' else None},amounts=[{'dimension':dimension,'value':value,'unit':unit,'basis':basis}],promote_to_medication=dimension=='dose')
        saved.append(save(c,body))
    totals=catalog(c)['totals']['groups']
    assert {(g['preparation'],g['known_subtotal'],g['unit']) for g in totals}=={('prbc','10','units'),('ffp','10','units'),('platelets_sdp','1','units'),('platelets_rdp','6','units'),('cryo','10','units'),('pcc','1000','IU'),('fibrinogen_concentrate','2','g')}
    assert len(catalog(c)['medication_exposures'])==2
    # A later individual episode is a distinct delivery, not a source correction.
    another=draft(repository);another['data'].update(product={'family':'prbc','preparation':'prbc','label':'PRBC'},amounts=[{'dimension':'count','value':'1','unit':'units','basis':'component units'}]);repeat=save(c,another)
    assert repeat['fact']['id']!=saved[0]['fact']['id'] and repeat['fact']['supersedes'] is None
    assert next(g for g in catalog(c)['totals']['groups'] if g['preparation']=='prbc')['known_subtotal']=='11'
