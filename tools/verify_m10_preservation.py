"""Read-only audit of the isolated M10 database against its captured M9 baseline."""
from pathlib import Path
import hashlib
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'review-evidence/m10'

def rows(connection, table):
    columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
    return columns, connection.execute(f'SELECT * FROM "{table}"').fetchall()

def main():
    manifest = json.loads((EVIDENCE / 'patient-preservation.json').read_text())
    baseline = sqlite3.connect(':memory:')
    baseline.executescript((EVIDENCE / 'patient-baseline.sql').read_text())
    current = sqlite3.connect(f"file:{manifest['destination']}?mode=ro", uri=True)
    protected = {}
    for table in ('patient', 'encounter', 'repository_identity', 'fact_revision', 'revision_link'):
        columns, original_rows = rows(baseline, table)
        new_columns, new_rows = rows(current, table)
        protected[table] = {'baseline_rows': len(original_rows), 'current_rows': len(new_rows), 'original_rows_preserved': columns == new_columns and set(original_rows).issubset(set(new_rows))}
    source_hash = hashlib.sha256(Path(manifest['source']).read_bytes()).hexdigest()
    result = {'source_database_unchanged': source_hash == manifest['source_sha256_before'], 'source_sha256': source_hash, 'isolated_integrity': current.execute('PRAGMA integrity_check').fetchone()[0], 'protected_tables': protected}
    result['passed'] = result['source_database_unchanged'] and result['isolated_integrity'] == 'ok' and all(t['original_rows_preserved'] for t in protected.values())
    (EVIDENCE / 'preservation-verified.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    current.close()
    baseline.close()
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
