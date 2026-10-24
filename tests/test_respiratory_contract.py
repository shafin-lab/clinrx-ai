"""Respiratory source contracts, checked only with disposable repositories."""
from hashlib import sha256
import pytest
from pydantic import ValidationError
from app.persistence.repository import transaction
from tests.test_laboratory_contract import report as lab_report, AT, TARGET
from test_persistence import database, registered


def record(version='1', **updates):
    from app.models.clinical.respiratory import RespiratoryRecord
    data=lab_report().model_dump(mode='json')
    for key in ('source_panel','specimen','components','original_report','original_report_digest'):data.pop(key)
    data.update(kind='respiratory_record',id='resp-'+sha256(b'lab.example\0respiratory-1').hexdigest()[:32],revision=version,
        category='blood_gas',title='Original arterial blood gas',
        source_identity={'issuer_namespace':'lab.example','source_report_id':'respiratory-1','source_version':version,'accession_id':'sample-1'},
        times={'occurred':{'status':'not_recorded'},'collected':{'status':'known','precision':'instant','value':AT.isoformat()},'reported':{'status':'known','precision':'instant','value':AT.isoformat()},'available':{'status':'known','precision':'instant','value':AT.isoformat()}},
        context={'sample_type':'arterial','population':'adult','settings_confirmed_at_sample':True},
        measurements=[{'concept':'pao2','label':'PO2 (source)','result':{'kind':'numeric','raw_value':'80.00','comparator':'=','unit':{'namespace':'source.unit','code':'mmHg','raw_display':'mmHg','version':None}},'role':'measured','quality':'usable','method':None}],
        narrative='Original report text',linked_sources=[])
    data.update(updates)
    return RespiratoryRecord.model_validate(data)


def test_exact_measurement_source_and_unknown_concept_survive():
    original=record()
    data=original.model_dump(mode='json');data['measurements'][0]['concept']='issuer.specialist.unknown'
    preserved=type(original).model_validate(data)
    assert preserved.measurements[0].result.raw_value=='80.00'
    assert preserved.measurements[0].concept=='issuer.specialist.unknown'
    assert preserved.context.reference_equation is None


@pytest.mark.parametrize('mutation',['version','duplicate','float','unbounded','correction','withdrawn','self_link'])
def test_invalid_contract_cannot_enter_storage(mutation):
    item=record();data=item.model_dump(mode='json')
    if mutation=='version':data['source_identity']['source_version']='other'
    if mutation=='duplicate':data['measurements']*=2
    if mutation=='float':data['measurements'][0]['result']['raw_value']=80.0
    if mutation=='unbounded':data['measurements']*=129
    if mutation=='correction':data['change_state']='corrected';data['report_status']='corrected'
    if mutation=='withdrawn':data['report_status']='withdrawn'
    if mutation=='self_link':data['linked_sources']=[item.reference.model_dump()]
    with pytest.raises(ValidationError):type(item).model_validate(data)


def test_append_revision_and_exact_retry_preserve_original_payload(registered):
    original=record()
    corrected=record('2',supersedes=original.reference,change_state='corrected',report_status='corrected',correction_reason='Issuer correction')
    with transaction(registered) as repo:
        first=repo.append_fact(original,target=TARGET)
        second=repo.append_revision(corrected,target=TARGET)
        retry=repo.append_fact(original,target=TARGET)
        assert retry==first
        assert repo.load_fact(original.reference,target=TARGET).fact.narrative=='Original report text'
        assert second.fact.supersedes==original.reference


@pytest.mark.parametrize('field',['settings_confirmed_at_sample','passive','occlusion_confirmed'])
@pytest.mark.parametrize('value',[1,'true'])
def test_sample_confirmation_requires_an_actual_boolean(field,value):
    original=record();data=original.model_dump(mode='json');data['context'][field]=value
    with pytest.raises(ValidationError):type(original).model_validate(data)


def test_m9_migration_preserves_all_171_original_fact_rows_and_links(tmp_path):
    """Exercise old schema upgrade without opening any patient database."""
    from alembic import command
    from alembic.config import Config
    from app.persistence.database import create_database
    from sqlalchemy import text
    from test_persistence import ROOT, fact, patient, encounter
    from app.persistence.canonical import canonical_payload
    engine=create_database(tmp_path/'m8-copy.sqlite3')
    config=Config(str(ROOT/'backend/alembic.ini'))
    try:
        with engine.begin() as connection:
            config.attributes['connection']=connection;command.upgrade(config,'m8_0009')
            connection.execute(text('INSERT INTO patient(patient_id,payload_version,payload,ingested_at) VALUES (:id,1,:payload,:at)'),{'id':TARGET.patient_id,'payload':canonical_payload(patient()),'at':AT.isoformat()})
            connection.execute(text('INSERT INTO encounter(encounter_id,patient_id,payload_version,payload,ingested_at) VALUES (:id,:patient,1,:payload,:at)'),{'id':TARGET.encounter_id,'patient':TARGET.patient_id,'payload':canonical_payload(encounter()),'at':AT.isoformat()})
            for index in range(170):
                item=fact(id=f'original-{index}')
                connection.execute(text('INSERT INTO fact_revision(kind,fact_id,revision,patient_id,encounter_id,payload_version,payload,ingested_at) VALUES (:kind,:id,:revision,:patient,:encounter,1,:payload,:at)'),{'kind':item.kind,'id':item.id,'revision':item.revision,'patient':TARGET.patient_id,'encounter':TARGET.encounter_id,'payload':canonical_payload(item),'at':AT.isoformat()})
            original=fact(id='original-0');corrected=fact(id='original-0',revision='2',supersedes=original.reference,correction_reason='Retained original correction')
            connection.execute(text('INSERT INTO fact_revision(kind,fact_id,revision,patient_id,encounter_id,payload_version,payload,ingested_at) VALUES (:kind,:id,:revision,:patient,:encounter,1,:payload,:at)'),{'kind':corrected.kind,'id':corrected.id,'revision':corrected.revision,'patient':TARGET.patient_id,'encounter':TARGET.encounter_id,'payload':canonical_payload(corrected),'at':AT.isoformat()})
            connection.exec_driver_sql('INSERT INTO revision_link VALUES(171,1)')
        def snapshot():
            with engine.connect() as c:
                names=[row[0] for row in c.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name!='alembic_version'").all()]
                return {name:c.exec_driver_sql(f'SELECT * FROM "{name}"').all() for name in names}
        before=snapshot();assert len(before['fact_revision'])==171
        with engine.begin() as connection:
            config.attributes['connection']=connection;command.upgrade(config,'head')
        after=snapshot()
        assert {name:after[name] for name in before}==before
        assert set(after)-set(before)=={'m10_command','m10_attachment'}
        assert after['m10_command']==after['m10_attachment']==[]
        with transaction(engine) as repo:
            assert repo.load_fact(original.reference,target=TARGET).fact==original
            assert repo.append_fact(record(),target=TARGET).ingestion.ingestion_sequence==172
        with engine.connect() as c:
            assert c.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
            assert c.exec_driver_sql('PRAGMA integrity_check').scalar_one()=='ok'
    finally:engine.dispose()


def test_optional_acquisition_metadata_roundtrips_without_changing_old_canonical_bytes():
    import json
    from pathlib import Path
    from app.persistence.canonical import canonical_payload
    from app.models.clinical.respiratory import RespiratoryRecord
    raw=Path('tests/fixtures/respiratory/legacy-source.json').read_bytes()
    assert len(raw)==6381
    assert sha256(raw).hexdigest()=='ad0fb4ff4311e2fa314ae77c78b6c55c5d5c32bcaac8da310b1eb11bf8eb38e2'
    original=RespiratoryRecord.model_validate_json(raw)
    assert canonical_payload(original)==raw.decode()
    assert all('acquisition' not in m for m in original.model_dump(mode='json')['measurements'])
    data=json.loads(raw);data['measurements'][0]['acquisition']={'breath_channel':'total','acquisition_id':'source-period-1'}
    updated=RespiratoryRecord.model_validate(data)
    assert updated.model_dump(mode='json')['measurements'][0]['acquisition']==data['measurements'][0]['acquisition']
    assert canonical_payload(RespiratoryRecord.model_validate_json(canonical_payload(updated)))==canonical_payload(updated)


def test_legacy_source_repository_exact_reimport_preserves_stored_bytes(registered):
    from pathlib import Path
    from app.models.clinical.respiratory import RespiratoryRecord
    from app.persistence.canonical import canonical_payload
    raw=Path('tests/fixtures/respiratory/legacy-source.json').read_text()
    source=RespiratoryRecord.model_validate_json(raw)
    with transaction(registered) as repo:
        original=repo.append_fact(source,target=TARGET)
        retried=repo.append_fact(RespiratoryRecord.model_validate_json(raw),target=TARGET)
        assert retried==original
        assert canonical_payload(repo.load_fact(source.reference,target=TARGET).fact)==raw
