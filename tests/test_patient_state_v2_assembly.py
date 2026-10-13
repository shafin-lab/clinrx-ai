"""M6.2 assembly assertions independent of mapping implementation."""
from datetime import timedelta
import pytest
from sqlalchemy import event, text
from app.execution.patient_state_v2_assembly import (AssemblyLimits, AssemblyRequestV2, assemble_patient_state_v2)
from app.persistence.bounded_history import HistoryBudget
from app.persistence.mapping import canonical_payload
from app.persistence.errors import QueryLimitExceeded, StorageIntegrityError
from test_persistence import database, registered, fact as old_fact
from test_patient_state_v2 import all_facts, facts, change, scope, AT, binding, code, c, time
from test_patient_state_v2_persistence import save, revision


def request(cutoff, **limits):
    return AssemblyRequestV2(scope=change(scope(),repository_cutoff=cutoff),
        profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2',limits=AssemblyLimits(**limits))


def assemble(engine, cutoff, **limits):
    return assemble_patient_state_v2(engine,request=request(cutoff,**limits))


@pytest.mark.parametrize('index',range(12))
def test_independent_fact_assembly(registered,index):
    fact=all_facts()[index]
    result=assemble(registered,save(registered,fact))
    assert [i.reference for i in result.snapshot.items]==[fact.reference]
    assert result.snapshot.items[0].ingestion is not None
    assert result.snapshot.items[0].expected_digest==fact.canonical_digest
    assert result.candidate_rows==1 and result.terminal_count==1


def test_all_groups_exact_distinct_and_read_only(registered,monkeypatch):
    records=all_facts()
    cutoff=save(registered,*records)
    import app.persistence.repository as repository
    monkeypatch.setattr(repository,'_now',lambda: pytest.fail('assembly sampled clock'))
    sql=[]
    def capture(conn,cursor,statement,params,context,many): sql.append(statement)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        first=assemble(registered,cutoff)
        second=assemble(registered,cutoff)
    finally: event.remove(registered,'before_cursor_execute',capture)
    assert first.canonical_digest==second.canonical_digest
    assert len(first.snapshot.items)==12
    assert all(o.disposition=='retained_exact' for o in first.bindings)
    assert first.snapshot.microbiology.isolates[0].susceptibilities==(records[2].reference,)
    assert first.snapshot.antimicrobial.orders==(records[4].reference,)
    assert first.snapshot.antimicrobial.administrations==(records[3].reference,)
    assert first.snapshot.antimicrobial.non_delivery==(records[11].reference,)
    assert sum(s=='BEGIN IMMEDIATE' for s in sql)==2
    assert not any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE')) for s in sql)
    registered.dispose()
    assert assemble(registered,cutoff).canonical_digest==first.canonical_digest


def test_historical_binding_not_rewritten(registered):
    specimen,isolate,susc,*_=facts()
    old=save(registered,specimen,isolate,susc)
    correction=revision(isolate,identification_state='final')
    new=save(registered,correction)
    before=assemble(registered,old)
    after=assemble(registered,new)
    assert next(o for o in before.bindings if o.owner==susc.reference).declared==isolate.reference
    outcome=next(o for o in after.bindings if o.owner==susc.reference)
    assert outcome.declared==isolate.reference and outcome.disposition=='historical_exact_not_retained'
    assert after.snapshot.microbiology.isolates[0].isolate==correction.reference
    assert after.snapshot.microbiology.isolates[0].susceptibilities==()
    assert next(i.fact for i in after.snapshot.items if i.reference==susc.reference).domain_bindings[0].exact==isolate.reference
    assert assemble(registered,old).canonical_digest==before.canonical_digest


@pytest.mark.parametrize('change_kind',['withdrawn','outside','missing','unknown_mapping'])
def test_terminal_before_mapping(registered,change_kind):
    original=facts()[2]
    old=save(registered,original)
    changes={}
    corrected_report=change(original.report,change='corrected')
    if change_kind=='withdrawn': changes['report']=change(corrected_report,status='withdrawn')
    elif change_kind=='outside': changes['report']=change(corrected_report,available=time(AT+timedelta(days=4)))
    elif change_kind=='missing': changes['report']=change(corrected_report,available=c.missing_time(),reported=c.missing_time())
    else: changes['antimicrobial']=change(original.antimicrobial,mapping_status='unknown',canonical_id=None,ingredient_ids=(),limitation='unknown')
    corrected=revision(original,**changes)
    new=save(registered,corrected)
    result=assemble(registered,new)
    assert original.reference not in [i.reference for i in result.snapshot.items]
    assert len(result.snapshot.items)==(0 if change_kind in ('withdrawn','outside') else 1)
    assert assemble(registered,old).snapshot.items[0].reference==original.reference


def test_context_exact_ancestors_only(registered):
    specimen,isolate,susc,*_=facts()
    specimen=change(specimen,collected=time(AT-timedelta(days=3)))
    isolate=change(isolate,report=change(isolate.report,available=time(AT-timedelta(days=2))))
    unrelated=change(specimen,id='unrelated',accession=code('other'))
    result=assemble(registered,save(registered,specimen,isolate,susc,unrelated))
    assert {i.reference for i in result.snapshot.items}=={specimen.reference,isolate.reference,susc.reference}
    parents={i.reference:i for i in result.snapshot.items if i.inclusion=='contextual_parent'}
    assert parents[specimen.reference].contextual_for==(isolate.reference,)
    assert parents[isolate.reference].contextual_for==(susc.reference,)
    assert parents[specimen.reference].fact.collected.value==AT-timedelta(days=3)


@pytest.mark.parametrize('state',['unresolved','ambiguous'])
def test_binding_uncertainty_retained(registered,state):
    isolate=facts()[1]
    b=change(binding(),status=state,exact=None,stable_target=None,limitation='source uncertain',
        candidates=(binding().exact,binding(id='S2').exact) if state=='ambiguous' else ())
    isolate=change(isolate,domain_bindings=(b,))
    result=assemble(registered,save(registered,isolate))
    assert result.bindings[0].status==state
    assert result.snapshot.items[0].fact.domain_bindings[0]==b


@pytest.mark.parametrize('index,field',[(0,'collected'),(3,'administered')])
def test_missing_times_retained_unplaced(registered,index,field):
    fact=change(facts()[index],**{field:c.missing_time()})
    result=assemble(registered,save(registered,fact))
    assert result.snapshot.items[0].inclusion=='unplaced'
    assert result.snapshot.items[0].fact.semantic_time.anchor is None
    assert any(i.reason=='temporal_incompleteness' for i in result.issues)


def test_same_names_are_not_identity(registered):
    specimen,isolate,susc,*_=facts()
    other=change(isolate,id='I2',isolate_identifier=code('I2'))
    test=change(susc,id='U2',test_identifier=code('test2'),domain_bindings=(binding('isolate','I2'),))
    result=assemble(registered,save(registered,specimen,isolate,other,susc,test))
    groups={g.isolate.id:g for g in result.snapshot.microbiology.isolates}
    assert groups['I'].susceptibilities==(susc.reference,)
    assert groups['I2'].susceptibilities==(test.reference,)


@pytest.mark.parametrize('limit', ['max_items','max_bindings','max_depth','max_fanout','max_traversal_steps','max_issues','max_result_bytes'])
def test_explicit_limits_never_truncate(registered,limit):
    records=list(all_facts())
    if limit=='max_issues':
        records[0]=change(records[0],collected=c.missing_time())
    cutoff=save(registered,*records)
    with pytest.raises(QueryLimitExceeded): assemble(registered,cutoff,**{limit:0 if limit=='max_depth' else 1})


@pytest.mark.parametrize('limit',['max_specimens','max_isolates','max_children','max_molecular_targets'])
def test_domain_bounds(registered,limit):
    records=list(all_facts())
    index={'max_specimens':0,'max_isolates':1,'max_children':2,'max_molecular_targets':8}[limit]
    records.append(change(records[index],id='second'))
    with pytest.raises(QueryLimitExceeded): assemble(registered,save(registered,*records),**{limit:1})


@pytest.mark.parametrize('budget',[HistoryBudget(max_rows=1),HistoryBudget(max_payload_bytes=1)])
def test_candidate_limits_before_decode(registered,budget,monkeypatch):
    cutoff=save(registered,*facts()[:2])
    import app.persistence.history as history
    monkeypatch.setattr(history,'load_fact',lambda *a: pytest.fail('decoded beyond budget'))
    with pytest.raises(QueryLimitExceeded): assemble(registered,cutoff,history=budget)


def test_unsupported_old_source_disclosed_not_coerced(registered):
    result=assemble(registered,save(registered,old_fact()))
    assert not result.snapshot.items
    assert result.issues[0].reason=='unsupported_source_structure'


def test_contradictory_bottle_is_hard_error(registered):
    records=list(all_facts())
    records[1]=change(records[1],domain_bindings=(binding(),binding('bottle','BOTTLE')))
    records[10]=change(records[10],domain_bindings=(binding('collection_set','SET'),binding(id='S2')))
    records.append(change(records[0],id='S2'))
    with pytest.raises(StorageIntegrityError): assemble(registered,save(registered,*records))


@pytest.mark.parametrize('limit',['max_items','max_specimens','max_isolates','max_children','max_molecular_targets'])
def test_exact_domain_limit_succeeds(registered,limit):
    indices={'max_items':0,'max_specimens':0,'max_isolates':1,'max_children':2,'max_molecular_targets':8}
    records=list(all_facts()) if limit=='max_children' else [all_facts()[indices[limit]]]
    cutoff=save(registered,*records)
    result=assemble(registered,cutoff,**{limit:1})
    assert len(result.snapshot.items)==len(records)


def test_exact_candidate_and_payload_budget(registered):
    original=facts()[0]
    cutoff=save(registered,original)
    size=len(canonical_payload(original).encode('utf-8'))
    result=assemble(registered,cutoff,history=HistoryBudget(max_rows=1,max_payload_bytes=size))
    assert result.candidate_rows==1
    with pytest.raises(QueryLimitExceeded): assemble(registered,cutoff,history=HistoryBudget(max_payload_bytes=size-1))


@pytest.mark.parametrize('offset,retained',[(0,True),(7200,True),(7200.000001,False),(-0.000001,False)])
def test_closed_display_boundary(registered,offset,retained):
    specimen=change(facts()[0],collected=time(AT+timedelta(seconds=offset)))
    result=assemble(registered,save(registered,specimen))
    assert bool(result.snapshot.items)==retained


def test_future_malformed_binding_target_is_not_read(registered):
    specimen,isolate,*_=facts()
    old=save(registered,isolate)
    save(registered,specimen)
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET payload='private-invalid' WHERE kind='microbiology_specimen'"))
    result=assemble(registered,old)
    assert result.bindings[0].disposition=='unavailable_in_prefix'


def test_foreign_binding_target_envelope_fails_without_decode(registered,monkeypatch):
    from app.persistence.errors import ScopeMismatch
    specimen,isolate,*_=facts()
    cutoff=save(registered,specimen,isolate)
    with registered.begin() as conn:
        conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2',payload='private-invalid' WHERE kind='microbiology_specimen'"))
    import app.persistence.history as module
    original=module.load_fact
    def guarded(row,*args):
        assert row.kind!='microbiology_specimen'
        return original(row,*args)
    monkeypatch.setattr(module,'load_fact',guarded)
    with pytest.raises(ScopeMismatch): assemble(registered,cutoff)


def test_sql_incidental_order_and_immutability(registered):
    cutoff=save(registered,*reversed(all_facts()))
    first=assemble(registered,cutoff)
    with registered.connect() as conn: conn.exec_driver_sql('PRAGMA reverse_unordered_selects=ON')
    second=assemble(registered,cutoff)
    assert first.canonical_digest==second.canonical_digest
    from pydantic import ValidationError
    with pytest.raises(ValidationError): second.snapshot.items[0].fact.id='changed'
    assert canonical_payload(type(first).model_validate_json(canonical_payload(first)))==canonical_payload(first)


def test_incomplete_report_and_unknown_mapping_are_not_corruption(registered):
    isolate=change(facts()[1],identification_state='unresolved',report=change(facts()[1].report,status='preliminary'))
    susc=change(facts()[2],result_status='indeterminate',mic=None,interpretation=None,
        antimicrobial=change(facts()[2].antimicrobial,mapping_status='unknown',canonical_id=None,ingredient_ids=(),limitation='unknown'))
    result=assemble(registered,save(registered,isolate,susc))
    assert len(result.snapshot.items)==2
    assert {'preliminary_report','unknown_isolate_identity','incomplete_susceptibility','unsupported_antimicrobial_mapping'} <= {i.reason for i in result.issues}


def test_unknown_availability_is_not_inferred_from_repository_cutoff(registered):
    isolate=change(facts()[1],report=change(facts()[1].report,available=c.missing_time()))
    result=assemble(registered,save(registered,isolate))
    retained=result.snapshot.items[0].fact
    assert retained.report.available.status=='not_recorded'
    assert retained.report.reported.value==AT


def test_namespaces_and_decimal_offset_retention(registered):
    specimen,isolate,susc,*_=facts()
    other=change(specimen,id='S2',accession=change(specimen.accession,namespace='another.lab'))
    result=assemble(registered,save(registered,specimen,other,isolate,susc))
    assert len(result.snapshot.microbiology.specimens)==2
    retained=next(i.fact for i in result.snapshot.items if i.reference==susc.reference)
    assert retained.mic.quantity.value.as_tuple().exponent==-3
    assert retained.report.available.value.isoformat()==AT.isoformat()


def test_withdrawn_exact_target_is_not_mislabeled_historical(registered):
    isolate=change(facts()[1],report=change(facts()[1].report,status='withdrawn'))
    susceptibility=facts()[2]
    result=assemble(registered,save(registered,isolate,susceptibility))
    outcome=result.bindings[0]
    assert outcome.declared==isolate.reference
    assert outcome.disposition=='withdrawn_target_not_retained'
    assert [i.reference for i in result.snapshot.items]==[susceptibility.reference]
    assert any(i.reason=='withdrawn_binding_target' for i in result.issues)
