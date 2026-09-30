"""Synthetic prefix history; no lineage or clinical reconstruction."""
from datetime import timedelta, timezone
import json
import os
import subprocess
import sys
import traceback
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.persistence.history import FactIdentity, ClinicalTimeFilter, IngestionTimeFilter
from app.persistence.errors import PersistenceInputError, ScopeMismatch, StorageIntegrityError
from app.persistence.repository import transaction
from test_persistence import AT, ROOT, TARGET, database, registered, fact, replace
from test_revision_chains import revision

KEY=FactIdentity(kind='observation', id='observation-1')


def build(engine):
    with transaction(engine) as repo:
        zero=repo.capture_cutoff()
        a1=repo.append_fact(fact(revision='z'),target=TARGET)
        c1=repo.capture_cutoff()
        b=repo.append_fact(fact(id='B'),target=TARGET)
        cb=repo.capture_cutoff()
        a2=repo.append_revision(revision(a1.fact,'10'),target=TARGET)
        c2=repo.capture_cutoff()
        a3=repo.append_revision(revision(a2.fact,'2'),target=TARGET)
        c3=repo.capture_cutoff()
    return (zero,c1,cb,c2,c3),(a1,b,a2,a3)


@pytest.mark.parametrize('stage,expected',[(0,[]),(1,['z']),(2,['z']),(3,['z','10']),(4,['z','10','2'])])
def test_history_and_latest_at_each_prefix(registered,stage,expected):
    cuts,stored=build(registered)
    with transaction(registered) as repo:
        history=repo.list_revisions(KEY,target=TARGET,cutoff=cuts[stage])
        latest=repo.load_latest_known(KEY,target=TARGET,cutoff=cuts[stage])
    assert [s.fact.revision for s in history.records]==expected
    assert [s.fact.revision for s in latest.records]==expected[-1:]
    assert history.cutoff==cuts[stage] and latest.cutoff==cuts[stage]


def test_scoped_latest_current_and_history(registered):
    cuts,(a1,b,a2,a3)=build(registered)
    with transaction(registered) as repo:
        assert repo.list_history(target=TARGET,cutoff=cuts[2]).records==(a1,b)
        assert repo.list_latest_known(target=TARGET,cutoff=cuts[2]).records==(a1,b)
        assert repo.list_latest_known(target=TARGET,cutoff=cuts[4]).records==(b,a3)
        current=repo.list_current_latest_known(target=TARGET)
        assert current==repo.list_latest_known(target=TARGET,cutoff=current.cutoff)
        single=repo.load_current_latest_known(KEY,target=TARGET)
        assert single==repo.load_latest_known(KEY,target=TARGET,cutoff=single.cutoff)
        assert repo.load_fact(a1.fact.reference,target=TARGET)==a1


@pytest.mark.parametrize('future_corruption',['none','payload','link'])
def test_old_prefix_unchanged_after_future_revision_and_corruption(registered,future_corruption):
    with transaction(registered) as repo:
        first=repo.append_fact(fact(),target=TARGET)
        cutoff=repo.capture_cutoff()
        before=repo.list_history(target=TARGET,cutoff=cutoff)
    with transaction(registered) as repo:
        later=repo.append_revision(revision(first.fact),target=TARGET)
    if future_corruption!='none':
        with registered.begin() as c:
            if future_corruption=='payload':
                c.execute(text("UPDATE fact_revision SET payload='{}' WHERE ingestion_sequence=:s"),{'s':later.ingestion.ingestion_sequence})
            else:
                c.execute(text('DELETE FROM revision_link'))
    with transaction(registered) as repo:
        after=repo.list_history(target=TARGET,cutoff=cutoff)
        assert after==before
        assert repo.load_latest_known(KEY,target=TARGET,cutoff=cutoff).records==(first,)
    assert not hasattr(after.records[0],'superseded_by')


@pytest.mark.parametrize('case',['foreign','negative','too_large','bool','text','fraction'])
def test_bad_cutoffs_revalidated(registered,case):
    cuts,_=build(registered)
    updates={'foreign':{'repository_id':uuid4()},'negative':{'fact_watermark':-1},
             'too_large':{'fact_watermark':999},'bool':{'fact_watermark':True},
             'text':{'fact_watermark':'1'},'fraction':{'fact_watermark':1.5}}
    bad=cuts[-1].model_copy(update=updates[case])
    with pytest.raises(ScopeMismatch if case=='foreign' else PersistenceInputError),transaction(registered) as repo:
        repo.list_history(target=TARGET,cutoff=bad)


@pytest.mark.parametrize('other',[replace(TARGET,encounter_id='synthetic-e2'),replace(TARGET,patient_id='synthetic-p2',encounter_id='synthetic-e3')])
def test_patient_encounter_isolation(registered,other):
    cuts,items=build(registered)
    with transaction(registered) as repo:
        another=repo.append_fact(fact(id='other',binding=replace(fact().binding,target=other)),target=other)
        cutoff=repo.capture_cutoff()
        assert repo.list_history(target=other,cutoff=cutoff).records==(another,)
        assert another not in repo.list_history(target=TARGET,cutoff=cutoff).records
    with pytest.raises(ScopeMismatch),transaction(registered) as repo:
        repo.list_revisions(KEY,target=other,cutoff=cutoff)


def test_sequence_gaps_and_empty_prefix(registered):
    with registered.begin() as c:
        c.execute(text("INSERT INTO sqlite_sequence(name,seq) VALUES ('fact_revision',9)"))
    with transaction(registered) as repo:
        first=repo.append_fact(fact(),target=TARGET)
        cutoff=repo.capture_cutoff()
        assert first.ingestion.ingestion_sequence==10
        assert repo.list_history(target=TARGET,cutoff=cutoff.model_copy(update={'fact_watermark':9})).records==()
        assert repo.list_history(target=TARGET,cutoff=cutoff).records==(first,)


@pytest.mark.parametrize('clock_values',[(AT,AT,AT),(AT,AT-timedelta(hours=1),AT-timedelta(hours=2))])
def test_equal_and_backward_ingestion_clock(registered,monkeypatch,clock_values):
    import app.persistence.repository as module
    originals=[]
    with transaction(registered) as repo:
        for index,at in enumerate(clock_values):
            monkeypatch.setattr(module,'_now',lambda at=at:at)
            originals.append(repo.append_fact(fact(id=str(index)),target=TARGET))
        cutoff=repo.capture_cutoff()
        assert repo.list_history(target=TARGET,cutoff=cutoff).records==tuple(originals)


@pytest.mark.parametrize('offset,expected',[(-1,False),(0,True),(1,True),(2,False)])
def test_event_half_open_boundaries(registered,offset,expected):
    with transaction(registered) as repo:
        original=repo.append_fact(fact(time=replace(fact().time,event=AT+timedelta(hours=offset),precision='instant')),target=TARGET)
        result=repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),clinical_filter=ClinicalTimeFilter(axis='event',start=AT,end=AT+timedelta(hours=2)))
        assert result.records==((original,) if expected else ())


@pytest.mark.parametrize('start,end,expected',[(-2,-1,False),(-1,0,True),(0,0,True),(1,3,True),(2,3,False),(1,None,True)])
def test_effective_overlap_boundaries(registered,start,end,expected):
    with transaction(registered) as repo:
        original=repo.append_fact(fact(time=replace(fact().time,precision='instant',effective_start=AT+timedelta(hours=start),effective_end=None if end is None else AT+timedelta(hours=end))),target=TARGET)
        result=repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),clinical_filter=ClinicalTimeFilter(axis='effective',start=AT,end=AT+timedelta(hours=2)))
        assert result.records==((original,) if expected else ())


@pytest.mark.parametrize('precision,missing,unknown,imprecise,expected',[
    ('unknown',True,False,False,False),('unknown',True,True,False,True),
    ('approximate',False,False,False,False),('approximate',False,False,True,True),
    ('day',False,False,False,False),('day',False,False,True,True),
    ('unknown',False,False,True,False),('unknown',False,True,False,True),
    ('instant',True,False,False,False),('instant',True,True,False,True)])
def test_unknown_and_imprecise_times(registered,precision,missing,unknown,imprecise,expected):
    with transaction(registered) as repo:
        original=repo.append_fact(fact(time=replace(fact().time,event=None if missing else AT,precision=precision)),target=TARGET)
        result=repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),clinical_filter=ClinicalTimeFilter(axis='event',start=AT,end=AT+timedelta(hours=1),include_unknown=unknown,include_imprecise=imprecise))
        assert bool(result.records)==expected
        if result.records: assert result.records[0]==original


def test_timezone_instants_and_no_mutation(registered):
    with transaction(registered) as repo:
        original=repo.append_fact(fact(time=replace(fact().time,precision='instant')),target=TARGET)
        cutoff=repo.capture_cutoff()
    def raw():
        with registered.connect() as c: return c.execute(text('SELECT * FROM fact_revision')).all()
    before=raw()
    with transaction(registered) as repo:
        result=repo.list_history(target=TARGET,cutoff=cutoff,clinical_filter=ClinicalTimeFilter(axis='event',start=AT.astimezone(timezone.utc),end=AT+timedelta(seconds=1)))
        assert result.records==(original,)
        assert result.records[0].fact.time.event.isoformat()==AT.isoformat()
    assert raw()==before


def test_corrected_event_and_ingestion_filters_never_resurrect_old_revision(registered,monkeypatch):
    import app.persistence.repository as module
    with transaction(registered) as repo:
        monkeypatch.setattr(module,'_now',lambda:AT)
        first=repo.append_fact(fact(time=replace(fact().time,precision='instant')),target=TARGET)
        old=repo.capture_cutoff()
        monkeypatch.setattr(module,'_now',lambda:AT+timedelta(hours=2))
        repo.append_revision(revision(first.fact,time=replace(first.fact.time,event=AT+timedelta(hours=2))),target=TARGET)
        current=repo.capture_cutoff()
        clinical=ClinicalTimeFilter(axis='event',start=AT,end=AT+timedelta(hours=1))
        ingestion=IngestionTimeFilter(start=AT,end=AT+timedelta(hours=1))
        for kwargs in ({'clinical_filter':clinical},{'ingestion_filter':ingestion}):
            assert repo.load_latest_known(KEY,target=TARGET,cutoff=current,**kwargs).records==()
            assert repo.load_latest_known(KEY,target=TARGET,cutoff=old,**kwargs).records==(first,)


def test_late_arrival_and_ingestion_filter_subordinate_to_prefix(registered,monkeypatch):
    import app.persistence.repository as module
    with transaction(registered) as repo:
        repo.append_fact(fact(),target=TARGET)
        old=repo.capture_cutoff()
        # Even a backdated ingestion timestamp cannot bypass the prefix boundary.
        monkeypatch.setattr(module,'_now',lambda:AT-timedelta(hours=4))
        later=repo.append_fact(fact(id='late',time=replace(fact().time,event=AT-timedelta(hours=5))),target=TARGET)
        window=IngestionTimeFilter(end=AT)
        assert repo.list_history(target=TARGET,cutoff=old,ingestion_filter=window).records==()
        assert repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),ingestion_filter=window).records==(later,)


@pytest.mark.parametrize('corruption',['payload','link','predecessor','identity','ingestion','owner'])
@pytest.mark.parametrize('method',['list_history','list_latest_known'])
def test_malformed_visible_storage_fails_before_filters(registered,corruption,method):
    cuts,(a1,b,a2,a3)=build(registered)
    with registered.begin() as c:
        if corruption=='payload':
            c.execute(text("UPDATE fact_revision SET payload='{}' WHERE ingestion_sequence=1"))
        elif corruption=='link':
            c.execute(text('DELETE FROM revision_link WHERE successor_sequence=3'))
        elif corruption=='predecessor':
            c.execute(text('UPDATE revision_link SET predecessor_sequence=2 WHERE successor_sequence=3'))
        elif corruption=='identity':
            c.execute(text("UPDATE fact_revision SET fact_id=' observation-1 ' WHERE ingestion_sequence=1"))
        elif corruption=='ingestion':
            c.execute(text("UPDATE fact_revision SET ingested_at='bad' WHERE ingestion_sequence=1"))
        else:
            # Payload no longer agrees with its relational envelope.
            c.execute(text("UPDATE fact_revision SET encounter_id='synthetic-e2' WHERE ingestion_sequence=1"))
    with pytest.raises((StorageIntegrityError,ScopeMismatch)),transaction(registered) as repo:
        getattr(repo,method)(target=TARGET,cutoff=cuts[-1],clinical_filter=ClinicalTimeFilter(axis='event',start=AT+timedelta(days=500)))


@pytest.mark.parametrize('parent',['patient','encounter'])
@pytest.mark.parametrize('corruption',['malformed','identity_mismatch'])
def test_history_validates_parents(registered,parent,corruption):
    from test_persistence_corrections import corrupt_parent
    cuts,_=build(registered)
    corrupt_parent(registered,parent,corruption)
    with pytest.raises(StorageIntegrityError),transaction(registered) as repo:
        repo.list_history(target=TARGET,cutoff=cuts[1])


@pytest.mark.parametrize('case',['cutoff','filter','stored'])
def test_history_error_privacy_and_no_warning_leak(registered,case):
    import warnings
    sentinel='CONFIDENTIAL_SYNTHETIC_HISTORY_SENTINEL'
    cuts,_=build(registered)
    cutoff=cuts[-1]
    kwargs={}
    expected=PersistenceInputError
    if case=='cutoff':
        cutoff=cutoff.model_copy(update={'fact_watermark':sentinel})
    elif case=='filter':
        kwargs['clinical_filter']={'axis':'event','start':sentinel}
    else:
        with registered.begin() as c:
            c.execute(text('UPDATE fact_revision SET payload=:p WHERE ingestion_sequence=1'),{'p':json.dumps({'private':sentinel})})
        expected=StorageIntegrityError
    with warnings.catch_warnings(record=True) as emitted:
        with pytest.raises(expected) as caught,transaction(registered) as repo:
            repo.list_history(target=TARGET,cutoff=cutoff,**kwargs)
    assert sentinel not in str(caught.value)
    assert sentinel not in repr(caught.value)
    assert sentinel not in ''.join(traceback.format_exception(caught.value))
    assert all(sentinel not in str(w.message) for w in emitted)


@pytest.mark.parametrize('window',[{'axis':'event'}, {'axis':'event','start':AT,'end':AT},
    {'axis':'event','start':AT,'end':AT-timedelta(seconds=1)},
    {'axis':'event','start':AT.replace(tzinfo=None)},
    {'axis':'bad','start':AT}, {'axis':'event','start':AT,'include_unknown':'yes'}])
def test_invalid_filter_contracts(registered,window):
    cuts,_=build(registered)
    with pytest.raises(PersistenceInputError),transaction(registered) as repo:
        repo.list_history(target=TARGET,cutoff=cuts[-1],clinical_filter=window)


def test_forged_filter_instance_is_revalidated(registered):
    cuts,_=build(registered)
    bad=ClinicalTimeFilter(axis='event',start=AT).model_copy(update={'axis':'bad'})
    with pytest.raises(PersistenceInputError),transaction(registered) as repo:
        repo.list_history(target=TARGET,cutoff=cuts[-1],clinical_filter=bad)


def test_restart_replays_identical_results(registered):
    cuts,_=build(registered)
    with transaction(registered) as repo:
        expected=repo.list_history(target=TARGET,cutoff=cuts[2])
    script='''
import json,sys
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.metadata import RepositoryCutoff
from app.models.clinical.common import ContextTarget
engine=create_database(sys.argv[1])
with transaction(engine) as repo:
    result=repo.list_history(target=ContextTarget.model_validate_json(sys.argv[2]),cutoff=RepositoryCutoff.model_validate_json(sys.argv[3]))
    print(json.dumps({'cutoff':result.cutoff.model_dump(mode='json'),'records':[{'fact':r.fact.model_dump(mode='json'),'ingestion':r.ingestion.model_dump(mode='json')} for r in result.records]}))
engine.dispose()
'''
    completed=subprocess.run([sys.executable,'-c',script,registered.url.database,TARGET.model_dump_json(),cuts[2].model_dump_json()],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'backend')})
    assert completed.returncode==0,completed.stderr
    assert json.loads(completed.stdout)=={'cutoff':expected.cutoff.model_dump(mode='json'),'records':[{'fact':r.fact.model_dump(mode='json'),'ingestion':r.ingestion.model_dump(mode='json')} for r in expected.records]}


def test_failed_query_aborts_prior_writes(registered):
    from app.persistence.errors import TransactionAborted
    with pytest.raises(TransactionAborted),transaction(registered) as repo:
        repo.append_fact(fact(),target=TARGET)
        cutoff=repo.capture_cutoff().model_copy(update={'fact_watermark':999})
        try: repo.list_history(target=TARGET,cutoff=cutoff)
        except PersistenceInputError: pass
    with transaction(registered) as repo:
        assert repo.list_history(target=TARGET,cutoff=repo.capture_cutoff()).records==()


def test_history_results_are_immutable(registered):
    from dataclasses import FrozenInstanceError
    from pydantic import ValidationError
    cuts,_=build(registered)
    with transaction(registered) as repo:
        result=repo.list_history(target=TARGET,cutoff=cuts[-1])
    with pytest.raises(FrozenInstanceError): result.records=()
    with pytest.raises(ValidationError): result.cutoff.fact_watermark=999
    with pytest.raises(ValidationError): result.records[0].fact.revision='changed'


def test_dst_fold_bounds_compare_instants(registered):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    zone=ZoneInfo('America/New_York')
    start=datetime(2026,11,1,1,45,tzinfo=zone,fold=0)
    end=datetime(2026,11,1,1,15,tzinfo=zone,fold=1)
    event_time=datetime.fromisoformat('2026-11-01T01:50:00-04:00')
    with transaction(registered) as repo:
        stored=repo.append_fact(fact(time=replace(fact().time,event=event_time,precision='instant')),target=TARGET)
        result=repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),clinical_filter=ClinicalTimeFilter(axis='event',start=start,end=end))
        assert result.records==(stored,)
        assert result.records[0].fact.time.event.isoformat()==event_time.isoformat()


@pytest.mark.parametrize('method',['list_revisions','load_latest_known','load_current_latest_known'])
@pytest.mark.parametrize('bad',[None, {'kind':'CONFIDENTIAL_IDENTITY_SENTINEL','id':'private'}])
def test_m1_single_identity_cannot_broaden(registered,method,bad):
    cuts,_=build(registered)
    with pytest.raises(PersistenceInputError) as caught,transaction(registered) as repo:
        kwargs={} if method=='load_current_latest_known' else {'cutoff':cuts[-1]}
        getattr(repo,method)(bad,target=TARGET,**kwargs)
    assert 'CONFIDENTIAL_IDENTITY_SENTINEL' not in str(caught.value)
    assert 'CONFIDENTIAL_IDENTITY_SENTINEL' not in repr(caught.value)
    assert 'CONFIDENTIAL_IDENTITY_SENTINEL' not in ''.join(traceback.format_exception(caught.value))
    with transaction(registered) as repo:
        assert len(repo.list_history(target=TARGET,cutoff=cuts[-1]).records)==4
        assert len(repo.list_latest_known(target=TARGET,cutoff=cuts[-1]).records)==2
        assert len(repo.list_current_latest_known(target=TARGET).records)==2
        assert len(repo.load_latest_known(KEY,target=TARGET,cutoff=cuts[-1]).records)==1


@pytest.mark.parametrize('method',['list_revisions','load_latest_known','load_current_latest_known'])
def test_m1_none_rejected_before_query_work(registered,method,monkeypatch):
    from app.persistence.errors import TransactionAborted
    with pytest.raises(TransactionAborted),transaction(registered) as repo:
        cutoff=repo.capture_cutoff()
        def forbidden(*args,**kwargs):
            raise AssertionError('query work preceded identity validation')
        monkeypatch.setattr(repo,'capture_cutoff',forbidden)
        monkeypatch.setattr(repo,'_target',forbidden)
        with pytest.raises(PersistenceInputError):
            kwargs={} if method=='load_current_latest_known' else {'cutoff':cutoff}
            getattr(repo,method)(None,target=TARGET,**kwargs)
        # A caught failed operation still aborts the transaction; reset is not
        # permitted, so let the enclosing context report its expected failure.
        from app.persistence.errors import TransactionAborted
        with pytest.raises(TransactionAborted): repo.list_history(target=TARGET,cutoff=cutoff)


BOUNDARIES=[
    '0001-01-01T00:00:00+05:30','0001-01-01T00:00:00-05:30',
    '9999-12-31T23:59:59.999999-05:30','9999-12-31T23:59:59.999999+05:30',
]


@pytest.mark.parametrize('stamp',BOUNDARIES)
@pytest.mark.parametrize('axis',['event','effective','ingestion'])
def test_s1_boundary_retention_and_filtering(registered,monkeypatch,stamp,axis):
    from datetime import datetime
    import app.persistence.repository as module
    at=datetime.fromisoformat(stamp)
    with transaction(registered) as repo:
        monkeypatch.setattr(module,'_now',lambda:at)
        original=fact(time=replace(fact().time,event=at,effective_start=at,effective_end=at,precision='instant'))
        stored=repo.append_fact(original,target=TARGET)
        cutoff=repo.capture_cutoff()
    with registered.connect() as c:
        before=c.execute(text('SELECT * FROM fact_revision')).all()
    with transaction(registered) as repo:
        def query(**bounds):
            kwargs={'ingestion_filter':IngestionTimeFilter(**bounds)} if axis=='ingestion' else {'clinical_filter':ClinicalTimeFilter(axis=axis,**bounds)}
            return repo.list_history(target=TARGET,cutoff=cutoff,**kwargs).records
        assert query(start=at)==(stored,)
        assert query(end=at)==()
        # Boundary values also compare normally against an ordinary modern bound.
        assert bool(query(start=AT))==(at.year==9999)
        assert bool(query(end=AT))==(at.year==1)
    with registered.connect() as c:
        assert c.execute(text('SELECT * FROM fact_revision')).all()==before
    assert stored.fact.time.event.isoformat()==at.isoformat()
    assert stored.ingestion.ingested_at.isoformat()==at.isoformat()


@pytest.mark.parametrize('year',[1,9999])
@pytest.mark.parametrize('contract',[ClinicalTimeFilter,IngestionTimeFilter])
def test_s1_two_boundary_query_bounds_ordered_exactly(year,contract):
    from datetime import datetime
    from pydantic import ValidationError
    base=datetime(year,1,1) if year==1 else datetime(year,12,31,23,59,59,999999)
    earlier=base.replace(tzinfo=timezone(timedelta(hours=5,minutes=30)))
    later=base.replace(tzinfo=timezone(timedelta(hours=-5,minutes=-30)))
    kwargs={'axis':'event'} if contract is ClinicalTimeFilter else {}
    assert contract(start=earlier,end=later,**kwargs).start==earlier
    with pytest.raises(ValidationError): contract(start=later,end=earlier,**kwargs)


@pytest.mark.parametrize('year',[1,9999])
def test_s1_boundary_equivalent_instants_and_microsecond_order(year):
    from datetime import datetime
    from app.persistence.history import _instant_key
    a=datetime(year,6,1,12,0,0,123456,tzinfo=timezone(timedelta(hours=5,minutes=45)))
    b=datetime(year,6,1,6,15,0,123456,tzinfo=timezone.utc)
    assert _instant_key(a)==_instant_key(b)
    assert _instant_key(b.replace(microsecond=123457))-_instant_key(a)==1


@pytest.mark.parametrize('bad',['0000-01-01T00:00:00+05:30','10000-01-01T00:00:00-05:30','0001-01-01T00:00:00'])
def test_s1_invalid_boundary_query_input_still_rejected(registered,bad):
    with pytest.raises(PersistenceInputError),transaction(registered) as repo:
        repo.list_history(target=TARGET,cutoff=repo.capture_cutoff(),clinical_filter={'axis':'event','start':bad})
