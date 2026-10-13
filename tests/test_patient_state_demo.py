"""Explicit deterministic bootstrap over the reviewed schema, never app startup."""
import ast
from pathlib import Path
from sqlalchemy import inspect
from app.demo import patient_state as demo
from app.persistence.database import create_database
from app.persistence.repository import transaction
from app.persistence.history import FactIdentity


def test_bootstrap_rerun_correction_and_reopen(tmp_path):
    path = tmp_path/'demo.sqlite3'; engine = create_database(path)
    try:
        first = demo.bootstrap(engine)
        assert first == demo.bootstrap(engine) == demo.manifest()
        with transaction(engine) as repo:
            assert repo.capture_cutoff().fact_watermark == 3
            facts = [repo.load_fact(f.reference, target=demo.TARGET).fact for f in demo.facts()]
        a,b,m = facts
        assert a.time.event < m.time.event < b.time.event
        assert a.id != b.id and a.provenance.source.identifier != b.provenance.source.identifier
        assert str(a.value.value.value)=='1.00' and str(b.value.value.value)=='2.000'
        assert len(inspect(engine).get_table_names()) == 10
        correction = demo.correct(engine)
        assert correction == demo.correct(engine)
        assert demo.bootstrap(engine) == first
    finally: engine.dispose()
    reopened = create_database(path)
    try:
        with transaction(reopened) as repo:
            cutoff = repo.capture_cutoff()
            assert cutoff.fact_watermark == 4
            history = repo.list_revisions(FactIdentity(kind='observation',id=a.id), target=demo.TARGET, cutoff=cutoff)
            assert [s.fact.revision for s in history.records] == ['1','2']
            assert history.records[-1].fact.supersedes == a.reference
    finally: reopened.dispose()


def test_demo_and_routes_have_no_direct_storage_or_test_imports():
    root = Path(__file__).resolve().parents[1]
    files = [root/'backend/app/demo/patient_state.py', *list((root/'backend/app/api/routes').glob('*.py'))]
    for path in files:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith(('test_', 'tests', 'pytest', 'sqlalchemy', 'app.persistence.entities'))
            if isinstance(node, ast.Call):
                name = getattr(node.func,'attr',getattr(node.func,'id',''))
                assert name not in ('execute','add','flush','commit','query','select') or path.name=='temporal_reviews.py' and name=='execute'



def test_explicit_cli_outside_repository_cwd(tmp_path):
    import json
    import os
    import subprocess
    import sys
    root=Path(__file__).resolve().parents[1]
    env={**os.environ,'PYTHONPATH':str(root/'backend'),'PYTHONDONTWRITEBYTECODE':'1'}
    path=tmp_path/'cli.sqlite3'
    result=subprocess.run([sys.executable,'-m','app.demo.patient_state','bootstrap','--database',str(path)],
        cwd=tmp_path,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)==demo.manifest()
    correction=subprocess.run([sys.executable,'-m','app.demo.patient_state','correct','--database',str(path)],
        cwd=tmp_path,env=env,capture_output=True,text=True,timeout=30)
    assert correction.returncode==0,correction.stderr
    assert json.loads(correction.stdout)['corrected']['version']=='2'
