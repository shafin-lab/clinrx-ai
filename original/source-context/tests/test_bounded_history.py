"""H1-B1 real SQLite admission boundaries, with independent expected evidence."""
from datetime import timedelta
import pytest
from sqlalchemy import event, text
from app.persistence import history
from app.persistence.bounded_history import HistoryBudget, AggregateHistoryBudget, HistoryAccounting
from app.persistence.history import FactIdentity, ClinicalTimeFilter, IngestionTimeFilter
from app.persistence.lineage import LineageLimits
from app.persistence.mapping import canonical_payload
from app.persistence.errors import QueryLimitExceeded, StorageIntegrityError, ScopeMismatch, TransactionAborted, PersistenceInputError
from app.persistence.repository import transaction
from app.persistence.shared_transaction import execution_transaction
from test_persistence import TARGET, AT, database, registered, fact, replace
from test_revision_chains import revision

KEY=FactIdentity(kind='observation',id='observation-1')

def save(engine,*facts):
    with transaction(engine) as repo:
        for f in facts:
            (repo.append_revision if f.supersedes else repo.append_fact)(f,target=TARGET)
        return repo.capture_cutoff()

def chain(engine,size=3):
    first=fact();values=[first]
    for n in range(1,size): values.append(revision(values[-1],str(n+1)))
    return save(engine,*values),values

def read(repo,cutoff,**kwargs):
    return repo.list_bounded_history(target=TARGET,cutoff=cutoff,budget=kwargs.pop('budget',HistoryBudget()),**kwargs)

def forbidden(*args,**kwargs): pytest.fail('payload decoded before admission')

@pytest.mark.parametrize('latest',[False,True])
@pytest.mark.parametrize('family',[False,True])
def test_exact_rows_and_bytes(registered,latest,family):
    cutoff,values=chain(registered)
    size=sum(len(canonical_payload(v).encode('utf-8')) for v in values)
    with transaction(registered) as repo:
        result=read(repo,cutoff,budget=HistoryBudget(max_rows=3,max_payload_bytes=size),identity=KEY if family else None,latest=latest)
    assert [s.fact.reference for s in result.records]==[v.reference for v in (values[-1:] if latest else values)]
    assert result.identity==(KEY if family else None)
    assert result.selection==('latest_known' if latest else 'history')
    assert result.cutoff==cutoff and result.target==TARGET

@pytest.mark.parametrize('resource',['row','byte','family_row','family_byte'])
def test_one_over_limit_no_decode(registered,monkeypatch,resource):
    cutoff,values=chain(registered)
    size=sum(len(canonical_payload(v).encode()) for v in values)
    kw={'budget':HistoryBudget(max_rows=2) if resource=='row' else HistoryBudget(max_payload_bytes=size-1) if resource=='byte' else HistoryBudget()}
    if resource.startswith('family_'):kw['family_budget']=HistoryBudget(max_rows=2) if resource=='family_row' else HistoryBudget(max_payload_bytes=size-1)
    monkeypatch.setattr(history,'load_fact',forbidden)
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo: read(repo,cutoff,**kw)


def test_utf8_bytes_not_characters(registered,monkeypatch):
    f=replace(fact(),uncertainty=('é漢😀',));cutoff=save(registered,f)
    raw=canonical_payload(f);size=len(raw.encode('utf-8'));assert size>len(raw)
    with transaction(registered) as repo:
        assert read(repo,cutoff,budget=HistoryBudget(max_payload_bytes=size)).records[0].fact==f
    monkeypatch.setattr(history,'load_fact',forbidden)
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        read(repo,cutoff,budget=HistoryBudget(max_payload_bytes=size-1))

@pytest.mark.parametrize('resource',['row','byte'])
def test_aggregate_across_families(registered,monkeypatch,resource):
    a=fact();b=fact(id='B');cutoff=save(registered,a,b)
    size=sum(len(canonical_payload(f).encode()) for f in (a,b))
    account=HistoryAccounting(AggregateHistoryBudget(max_rows=1 if resource=='row' else 2,max_payload_bytes=size-1 if resource=='byte' else size))
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        read(repo,cutoff,identity=KEY,accounting=account)
        monkeypatch.setattr(history,'load_fact',forbidden)
        read(repo,cutoff,identity=FactIdentity(kind='observation',id='B'),accounting=account)
    assert account.rows==1 and account.payload_bytes==len(canonical_payload(a).encode())


def test_repeated_reads_charge_full_history_even_when_latest(registered,monkeypatch):
    cutoff,values=chain(registered);size=sum(len(canonical_payload(v).encode()) for v in values)
    account=HistoryAccounting(AggregateHistoryBudget(max_rows=6,max_payload_bytes=2*size))
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        for _ in range(2): assert len(read(repo,cutoff,identity=KEY,latest=True,accounting=account).records)==1
        assert account.rows==6 and account.payload_bytes==2*size
        monkeypatch.setattr(history,'load_fact',forbidden)
        read(repo,cutoff,identity=KEY,accounting=account)
    assert account.rows==6


def test_filtered_records_still_charge_entire_chain(registered):
    cutoff,values=chain(registered);account=HistoryAccounting(AggregateHistoryBudget())
    window=ClinicalTimeFilter(axis='event',start=AT+timedelta(days=1))
    with transaction(registered) as repo:
        assert read(repo,cutoff,identity=KEY,latest=True,clinical_filter=window,accounting=account).records==()
    assert account.rows==3


def test_empty_family_is_explicit_and_charges_zero(registered):
    cutoff=save(registered,fact());account=HistoryAccounting(AggregateHistoryBudget())
    with transaction(registered) as repo:
        result=read(repo,cutoff,identity=FactIdentity(kind='observation',id='absent'),accounting=account)
    assert not result.records and account.rows==account.payload_bytes==0

@pytest.mark.parametrize('corruption',['payload','ownership','link'])
def test_future_revision_does_not_consume_or_influence_old_prefix(registered,corruption):
    f=fact();old=save(registered,f);new=save(registered,revision(f))
    with registered.begin() as conn:
        if corruption=='payload':conn.execute(text("UPDATE fact_revision SET payload='invalid' WHERE revision='2'"))
        elif corruption=='ownership':conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2' WHERE revision='2'"))
        else:conn.execute(text('DELETE FROM revision_link'))
    size=len(canonical_payload(f).encode());account=HistoryAccounting(AggregateHistoryBudget(max_rows=1,max_payload_bytes=size))
    with transaction(registered) as repo:
        assert read(repo,old,identity=KEY,latest=True,budget=HistoryBudget(max_rows=1,max_payload_bytes=size),accounting=account).records[0].fact.reference==f.reference
    assert account.rows==1 and account.payload_bytes==size


def test_unrelated_families_not_read_by_exact_family_query(registered):
    f=fact();cutoff=save(registered,f,fact(id='B'))
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET payload='invalid' WHERE fact_id='B'"))
    with transaction(registered) as repo:
        assert read(repo,cutoff,identity=KEY,budget=HistoryBudget(max_rows=1)).records[0].fact==f
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:read(repo,cutoff)

@pytest.mark.parametrize('family',[False,True])
def test_foreign_successor_rejected_before_payload_decode(registered,monkeypatch,family):
    cutoff,_=chain(registered,2)
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2',payload='invalid' WHERE revision='2'"))
    monkeypatch.setattr(history,'load_fact',forbidden)
    with pytest.raises(ScopeMismatch),transaction(registered) as repo:read(repo,cutoff,identity=KEY if family else None)

@pytest.mark.parametrize('damage',['payload','link','predecessor'])
def test_admitted_corruption_is_integrity_failure(registered,damage):
    cutoff,_=chain(registered,2)
    with registered.begin() as conn:
        if damage=='payload':conn.execute(text("UPDATE fact_revision SET payload='invalid' WHERE revision='2'"))
        elif damage=='link':conn.execute(text('DELETE FROM revision_link'))
        else:
            import json
            payload=conn.execute(text("SELECT payload FROM fact_revision WHERE revision='2'")).scalar_one()
            body=json.loads(payload);body['supersedes']['version']='absent'
            conn.execute(text("UPDATE fact_revision SET payload=:p WHERE revision='2'"),{'p':json.dumps(body)})
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:read(repo,cutoff,identity=KEY)


def test_terminal_before_time_filter_no_resurrection(registered):
    f=fact();newer=replace(revision(f),time=replace(f.time,event=AT+timedelta(days=1)))
    cutoff=save(registered,f,newer)
    window=ClinicalTimeFilter(axis='event',start=AT-timedelta(seconds=1),end=AT+timedelta(seconds=1),include_imprecise=True)
    with transaction(registered) as repo:
        assert read(repo,cutoff,identity=KEY,latest=True,clinical_filter=window).records==()
        assert [s.fact.reference for s in read(repo,cutoff,identity=KEY,clinical_filter=window).records]==[f.reference]


def test_withdrawn_terminal_is_returned_not_resurrected(registered):
    from test_patient_state_v2 import facts,change
    f=facts()[2];newer=change(f,revision='2',supersedes=f.reference,correction_reason='Synthetic withdrawal',report=change(f.report,status='withdrawn',change='corrected'))
    cutoff=save(registered,f,newer)
    with transaction(registered) as repo:
        result=read(repo,cutoff,identity=FactIdentity(kind=f.kind,id=f.id),latest=True)
    assert len(result.records)==1 and result.records[0].fact.report.status=='withdrawn'
    assert result.records[0].fact.reference==newer.reference

@pytest.mark.parametrize('family',[False,True])
@pytest.mark.parametrize('latest',[False,True])
def test_legacy_result_exact_compatibility(registered,family,latest):
    cutoff,_=chain(registered)
    with transaction(registered) as repo:
        kwargs=dict(target=TARGET,cutoff=cutoff)
        if family:legacy=(repo.load_latest_known if latest else repo.list_revisions)(KEY,**kwargs)
        else:legacy=(repo.list_latest_known if latest else repo.list_history)(**kwargs)
        assert read(repo,cutoff,identity=KEY if family else None,latest=latest)==legacy


def test_every_history_payload_and_link_query_has_sql_limit(registered):
    cutoff,_=chain(registered);queries=[]
    def capture(conn,cursor,sql,parameters,context,many): queries.append(sql)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        with transaction(registered) as repo:read(repo,cutoff)
    finally:event.remove(registered,'before_cursor_execute',capture)
    selected=[q for q in queries if q.lstrip().upper().startswith('SELECT') and ('FROM fact_revision' in q or 'FROM revision_link' in q)]
    assert selected and all('LIMIT' in q or 'max(' in q for q in selected)
    assert not any('SELECT DISTINCT' in q for q in selected)


def test_serialized_limits_unchanged():
    assert HistoryBudget().model_dump()=={'max_rows':4096,'max_payload_bytes':16777216}
    assert set(LineageLimits().model_dump())=={'max_records','max_nodes','max_assertions','max_width','max_depth','max_ancestry_entries'}

@pytest.mark.parametrize('value',[object(),{'rows':0}])
def test_invalid_accounting_poisoned(registered,value):
    cutoff=save(registered,fact())
    with pytest.raises(PersistenceInputError),execution_transaction(registered) as tx:
        read(tx.repository,cutoff,accounting=value)


def test_caught_exhaustion_poisoned_no_further_sql_and_rolls_back(registered):
    cutoff=save(registered,fact());queries=[]
    def capture(conn,cursor,sql,parameters,context,many):queries.append(sql)
    event.listen(registered,'before_cursor_execute',capture)
    try:
        with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
            tx.repository.append_fact(fact(id='provisional'),target=TARGET)
            current=tx.repository.capture_cutoff()
            with pytest.raises(QueryLimitExceeded):read(tx.repository,current,budget=HistoryBudget(max_rows=1))
            count=len(queries)
            with pytest.raises(TransactionAborted):tx.repository.capture_cutoff()
            assert len(queries)==count
    finally:event.remove(registered,'before_cursor_execute',capture)
    with pytest.raises(TransactionAborted):tx.repository.capture_cutoff()
    with transaction(registered) as repo:
        assert repo.capture_cutoff().fact_watermark==cutoff.fact_watermark
        assert [s.fact.id for s in repo.list_history(target=TARGET,cutoff=cutoff).records]==['observation-1']
    assert sum(q=='BEGIN IMMEDIATE' for q in queries)==1

@pytest.mark.parametrize('resource',['row','byte'])
def test_lineage_row_and_byte_admission(registered,monkeypatch,resource):
    cutoff=save(registered,fact())
    monkeypatch.setattr(history,'load_fact',forbidden)
    if resource=='row':
        cutoff=save(registered,fact(id='B'))
        kw={'limits':LineageLimits(max_records=1)}
    else:kw={'limits':LineageLimits(),'history_budget':HistoryBudget(max_payload_bytes=1)}
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        repo.resolve_lineage(fact().reference,target=TARGET,cutoff=cutoff,**kw)


def test_lineage_accounting_preserves_result(registered):
    cutoff=save(registered,fact());account=HistoryAccounting(AggregateHistoryBudget())
    with transaction(registered) as repo:
        legacy=repo.resolve_lineage(fact().reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())
        bounded=repo.resolve_lineage(fact().reference,target=TARGET,cutoff=cutoff,limits=LineageLimits(),history_budget=HistoryBudget(),accounting=account)
    assert bounded==legacy and account.rows==1

@pytest.mark.parametrize('mode',['same_value','provenance'])
def test_correction_content_does_not_change_chain_accounting(registered,mode):
    f=fact();newer=revision(f)
    if mode=='provenance':newer=replace(newer,provenance=replace(newer.provenance,actor='changed-source'))
    cutoff=save(registered,f,newer);account=HistoryAccounting(AggregateHistoryBudget(max_rows=2))
    with transaction(registered) as repo:
        result=read(repo,cutoff,identity=KEY,latest=True,accounting=account)
    assert result.records[0].fact==newer and account.rows==2


def test_per_family_limit_not_confused_with_total_rows(registered):
    a=fact();a2=revision(a);b=fact(id='B');cutoff=save(registered,a,a2,b)
    with transaction(registered) as repo:
        assert len(read(repo,cutoff,budget=HistoryBudget(max_rows=3),family_budget=HistoryBudget(max_rows=2)).records)==3
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        read(repo,cutoff,budget=HistoryBudget(max_rows=3),family_budget=HistoryBudget(max_rows=1))


def test_admitted_corruption_charged_but_never_returned(registered):
    cutoff=save(registered,fact());account=HistoryAccounting(AggregateHistoryBudget())
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET payload='invalid'"))
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:read(repo,cutoff,accounting=account)
    assert account.rows==1 and account.payload_bytes==len('invalid'.encode())


def test_aggregate_reservation_properties_not_settable():
    account=HistoryAccounting(AggregateHistoryBudget())
    for field in ('rows','payload_bytes'):
        with pytest.raises(AttributeError):setattr(account,field,0)

@pytest.mark.parametrize('latest',[1,'false',None])
def test_invalid_selection_mode_fails_before_sql(registered,latest):
    cutoff=save(registered,fact());queries=[]
    with pytest.raises(TransactionAborted),execution_transaction(registered) as tx:
        def capture(conn,cursor,sql,parameters,context,many):queries.append(sql)
        event.listen(registered,'before_cursor_execute',capture)
        try:
            with pytest.raises(PersistenceInputError):read(tx.repository,cutoff,latest=latest)
            assert queries==[]
        finally:event.remove(registered,'before_cursor_execute',capture)


def test_lineage_default_byte_cap_before_decode(registered,monkeypatch):
    cutoff=save(registered,fact())
    with registered.begin() as conn:conn.execute(text('UPDATE fact_revision SET payload=:p'),{'p':'x'*(16777216+1)})
    monkeypatch.setattr(history,'load_fact',forbidden)
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        repo.resolve_lineage(fact().reference,target=TARGET,cutoff=cutoff,limits=LineageLimits())


def test_lineage_preserves_row_allowance_above_4096(registered):
    from app.persistence.entities import FactRow
    # Fixtures intentionally use bulk SQL; this is existing-schema capacity evidence,
    # not a new production bulk-ingestion interface.
    rows=[]
    for n in range(4097):
        f=fact(id='bulk-'+str(n));rows.append(dict(kind=f.kind,fact_id=f.id,revision=f.revision,patient_id=TARGET.patient_id,
            encounter_id=TARGET.encounter_id,payload=canonical_payload(f),payload_version=1,ingested_at=AT.isoformat()))
    with registered.begin() as conn:conn.execute(FactRow.__table__.insert(),rows)
    with transaction(registered) as repo:
        cutoff=repo.capture_cutoff()
        result=repo.resolve_lineage(fact(id='bulk-0').reference,target=TARGET,cutoff=cutoff,limits=LineageLimits(max_records=4097))
    assert [n.stored.fact.id for n in result.nodes]==['bulk-0']


def test_lineage_exact_bytes_and_repeated_aggregate_exhaustion(registered):
    f=fact();cutoff=save(registered,f);size=len(canonical_payload(f).encode());account=HistoryAccounting(AggregateHistoryBudget(max_rows=1,max_payload_bytes=size))
    with pytest.raises(QueryLimitExceeded),transaction(registered) as repo:
        first=repo.resolve_lineage(f.reference,target=TARGET,cutoff=cutoff,limits=LineageLimits(),history_budget=HistoryBudget(max_payload_bytes=size),accounting=account)
        assert first.nodes[0].stored.fact==f
        repo.resolve_lineage(f.reference,target=TARGET,cutoff=cutoff,limits=LineageLimits(),history_budget=HistoryBudget(max_payload_bytes=size),accounting=account)
    assert account.rows==1 and account.payload_bytes==size

from test_weight_trend_execution_persistence import case,make_record


def test_exhaustion_rolls_back_provisional_execution_and_facts(case,registered):
    record=make_record(case)
    with transaction(registered) as repo:before=repo.capture_cutoff()
    with pytest.raises(QueryLimitExceeded),execution_transaction(registered) as tx:
        tx.executions.append(record,target=TARGET)
        tx.repository.append_fact(fact(id='provisional'),target=TARGET)
        cutoff=tx.repository.capture_cutoff()
        read(tx.repository,cutoff,budget=HistoryBudget(max_rows=1))
    with registered.connect() as conn:assert conn.execute(text('SELECT count(*) FROM weight_trend_execution')).scalar_one()==0
    with transaction(registered) as repo:assert repo.capture_cutoff().fact_watermark==before.fact_watermark


def test_malformed_identity_is_integrity_failure_before_decode(registered,monkeypatch):
    cutoff=save(registered,fact(),fact(id='B'))
    with registered.begin() as conn:conn.execute(text("UPDATE fact_revision SET fact_id=:id WHERE fact_id='B'"),{'id':b'B'})
    monkeypatch.setattr(history,'load_fact',forbidden)
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:read(repo,cutoff)
