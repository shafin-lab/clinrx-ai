"""Portable read-only checks; no application execution or third-party dependencies."""
from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((p/'SHA256SUMS.json').read_text())
for f,h in manifest.items():assert sha((p/f).read_bytes())==h,f
for f,h in json.loads((p/'original/SHA256SUMS.json').read_text()).items():assert sha((p/'original'/f).read_bytes())==h,f
identity=json.loads((p/'source-identity.json').read_text());assert len(identity['files'])==2
for f,h in identity['files'].items():assert sha((p/'source'/f).read_bytes())==h,f
for line in (p/'original/tested-source.sha256').read_text().splitlines():
 h,f=line.split('  ',1);assert identity['files'][f]==h,f
commit=(p/'source-commit.txt').read_bytes()
assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==identity['source']
assert commit.startswith(('tree '+identity['tree']+'\nparent '+identity['parent']+'\n').encode())
assert '9 passed' in (p/'original/focused.log').read_text()
assert 'tsc --noEmit && vite build' in (p/'original/build.log').read_text() and 'built in' in (p/'original/build.log').read_text()
shot=p/'original/qualitative-echo.jpg';assert shot.suffix=='.jpg' and shot.read_bytes().startswith(b'\xff\xd8\xff')
dom=(p/'original/current-dom.txt').read_text()
for text in ['Recorded production tag: direct measurement','Qualitative echo findings are source-report assertions, not directly measured diagnoses. The recorded production tag is preserved as supplied.','no invasive confirmation or PAH subtype established','New execution disabled in this demo','Chart source m7-PH revision 1','2026-10-08 08:00:00']:assert text in dom,text
assert 'Source production:' not in dom
print(json.dumps({'result':'PASS','manifest_entries':len(manifest),'committed_tested_files_match':2,'raw_commit_identity':identity['source'],'focused_tests':9,'screenshot_bytes_and_extension':'JPEG/.jpg match','qualitative_clarification_and_original_report_visible':True,'execution_disabled_banner':True,'scope':'Implementation data-only checks; not independent review, a new full-suite run or a complete browser/network trace'},indent=2))
