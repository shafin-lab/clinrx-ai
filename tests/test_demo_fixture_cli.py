"""Offline fixture packaging exits cleanly and never replaces an existing database."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from starlette.testclient import TestClient
from app.demo.hosting import SyntheticDemoGateway, PREFIX


def build(path,*options):
    return subprocess.run([sys.executable,'-m','app.demo.comprehensive','--database',str(path),*options],
        cwd=Path(__file__).resolve().parents[1],env={**os.environ,'PYTHONPATH':'backend','PYTHONDONTWRITEBYTECODE':'1'},
        capture_output=True,text=True,timeout=60)


@pytest.mark.parametrize('expanded,count',[pytest.param(False,41,id='unchanged-default'),pytest.param(True,156,id='docker-flowsheet')])
def test_offline_cli_retains_database_emits_manifest_and_browses_actual_fixture(tmp_path,expanded,count):
    path=tmp_path/'fixture.sqlite3';result=build(path,*(['--flowsheet'] if expanded else []))
    assert result.returncode==0,result.stderr
    manifest=json.loads(result.stdout)
    assert manifest['dataset']==('synthetic-icu-flowsheet/2' if expanded else 'comprehensive-synthetic-demo/2')
    assert manifest['execution_enabled'] is False and manifest['optional_hpi_included'] is False
    assert manifest['recorded_families']==14
    with sqlite3.connect(path) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    frontend=tmp_path/'dist';(frontend/'assets').mkdir(parents=True);(frontend/'index.html').write_text('demo')
    with TestClient(SyntheticDemoGateway(path,frontend,'a7'*32)) as client:
        response=client.get(PREFIX+'/patient-state-v3',params={k:manifest[k] for k in ('review_start','review_end')})
        assert response.status_code==200 and response.json()['execution_enabled'] is False
        assert len(response.json()['assembly']['snapshot']['items'])==count
    before=path.read_bytes();refused=build(path,'--flowsheet')
    assert refused.returncode==2 and path.read_bytes()==before


@pytest.mark.parametrize('kind',['empty','sentinel','symlink','dangling'])
def test_offline_cli_refuses_every_existing_path_without_modification(tmp_path,kind):
    path=tmp_path/'existing.sqlite3';target=tmp_path/'target'
    if kind in ('symlink','dangling'):
        if kind=='symlink':target.write_bytes(b'preserved-target')
        path.symlink_to(target)
    else:path.write_bytes(b'' if kind=='empty' else b'preserved-bytes')
    before=target.read_bytes() if target.exists() else (path.read_bytes() if not path.is_symlink() else None)
    result=build(path,'--flowsheet');assert result.returncode==2
    if path.is_symlink():
        assert path.readlink()==target
        assert (target.read_bytes() if target.exists() else None)==before
    else:assert path.read_bytes()==before


def test_cli_rejects_relative_path_without_creating_file():
    result=build('never-created-relative.sqlite3','--flowsheet')
    assert result.returncode==2 and not Path('never-created-relative.sqlite3').exists()
