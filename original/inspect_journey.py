from pathlib import Path
import sqlite3,json,hashlib,shutil,subprocess
root=Path.cwd().parent;out=root/'rf2-f2-compatibility-validation';journey=out/'assisted-journey';journey.mkdir(exist_ok=True)
old=root/'rf2-f123-validation/runtime-after.sqlite3';live=root/'rf2-milestone-validation/runtime/synthetic.sqlite3'
with sqlite3.connect(f'file:{live}?mode=ro',uri=True) as db,sqlite3.connect(journey/'publication-checkpoint.sqlite3') as checkpoint:
 assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.backup(checkpoint)
 tables=[x[0] for x in db.execute("select name from sqlite_master where type='table' order by name")]
 after={t:db.execute('select * from "'+t+'" order by rowid').fetchall() for t in tables}
 payloads={row[0]:json.loads(row[7]) for row in after['fact_revision']}
with sqlite3.connect(old) as db:before={t:db.execute('select * from "'+t+'" order by rowid').fetchall() for t in tables}
assert len(before['fact_revision'])==182 and len(after['fact_revision'])==186
assert before['fact_revision']==after['fact_revision'][:182]
changed=[t for t in tables if before[t]!=after[t]];assert changed==['fact_revision','revision_link','sqlite_sequence'],changed
assert after['revision_link'][:len(before['revision_link'])]==before['revision_link']
assert len(after['revision_link'])-len(before['revision_link'])==3
assert len(after['circulatory_execution'])==2 and before['circulatory_execution']==after['circulatory_execution']
for name,value in [('prior-182-rows.json',before),('publication-186-rows.json',after)]:
 (journey/name).write_text(json.dumps(value,indent=2)+'\n')
notes={seq:{'id':f['id'],'revision':f['revision'],'amount':f.get('recorded_amount'),'reason':f.get('correction_reason'),'supersedes':f.get('supersedes')} for seq,f in payloads.items() if seq>=183}
(journey/'ADDITIONS-183-186.json').write_text(json.dumps(notes,indent=2)+'\n')
for seq in [64,183,184,185,186]:(journey/f'fact-{seq}.json').write_text(json.dumps(payloads[seq],indent=2)+'\n')
pasted=Path('/Users/mohammedshafiqshajahan/.codex/attachments/b305f1e0-f8cf-4115-be83-c903d98b7d38/Pasted text.txt');shutil.copyfile(pasted,journey/'user-pasted-expanded-reassessment.txt')
v,end=json.JSONDecoder().raw_decode(pasted.read_text().lstrip());assert v['fact']==payloads[186]
urine=v['metadata']['note']['pins'][0];assert urine['reference']=={'kind':'circulatory_event','id':'fs-IO-output_urine-45','version':payloads[185]['revision']}
assert urine['digest']==hashlib.sha256(json.dumps(payloads[185],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
# Keep supplied originals private/local: screenshots include unrelated ChatGPT sidebar content.
paths=[('saved-two-selections','NSIRD_screencaptureui_WC9C3I/Screenshot 2026-10-20 at 2.06.52\u202fPM.png'),('restored-two-selections','NSIRD_screencaptureui_EtswjI/Screenshot 2026-10-20 at 2.11.26\u202fPM.png'),('restored-both-cards','NSIRD_screencaptureui_IkspPw/Screenshot 2026-10-20 at 2.36.54\u202fPM.png')]
images=[]
for label,rel in paths:
 p=Path('/var/folders/r9/4k0mh4sd5vgghvrds28byzqw0000gn/T/TemporaryItems')/rel
 if p.exists():
  dest=journey/(label+'.png');shutil.copyfile(p,dest);b=dest.read_bytes();assert b.startswith(b'\x89PNG\r\n\x1a\n');images.append({'path':dest.name,'sha256':hashlib.sha256(b).hexdigest(),'attribution':'User supplied; not agent-operated; original includes unrelated sidebar and must not be published without separate sanitisation/authorization.'})
 else:images.append({'path':str(p),'missing':True})
(journey/'USER-SCREENSHOTS-LOCAL-ONLY.json').write_text(json.dumps(images,indent=2)+'\n')
(journey/'ATTRIBUTION.md').write_text('''# Assisted journey: later publication correspondence

Application runtime/build attribution remains 757b163; source correction work afterwards is separate. User operated the browser with extensive step-by-step assistance. Screenshots were supplied by the user, not independently captured by the agent. Reload is user-reported; the later screenshot displays the Restored status and previous saved timestamp. No authenticated network trace or localStorage export exists.

The 186-row SQLite checkpoint is captured later for publication. It is NOT a contemporaneous before/after checkpoint for each click. The earlier genuine 182-row checkpoint is unchanged; all 182 old rows and both receipts match. Only four fact additions, their three new revision links, and the expected sequence counter differ across all twelve tables. All prior revision links remain unchanged.

183: preliminary same-value urine-15 amendment (35 mL), reason patient updation. 184: preliminary same-value urine-30 amendment (25 mL), same reason. These are stored records; the agent did not witness those individual actions and does not infer why they were submitted. 185: urine-45 correction 40 to 45 mL. 186: new authored reassessment. Do not describe all four additions as only the intended correction and note.

The user-pasted expanded record equals the later stored reassessment payload exactly. Its three pins and review decisions retain exact urine/weight/fluid references. The stored corrected quantity string is 45; four-place formatting is not established. The original record at ingestion64 remains 40 mL.

Screenshots are preserved locally unmodified and retain matching PNG extensions. They include unrelated sidebar/chat material and are not automatically approved for public publication. No images have been redacted or regenerated. No new browser exercise, uncoached usability, accessibility, pending-command recovery or clinical acceptance is claimed.
''')
print(json.dumps({'all_prior_182_rows_preserved':True,'all_tables':len(tables),'changed_tables':changed,'receipt_rows_preserved':2,'new_facts':list(notes),'pasted_record_matches_database':True,'local_original_screenshots':len(images)},indent=2))
