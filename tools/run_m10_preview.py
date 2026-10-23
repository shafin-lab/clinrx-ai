"""Run only the isolated M10 preview and its copied synthetic database."""
import argparse
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'review-evidence/m10'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend',type=Path,required=True)
    args=parser.parse_args()
    frontend=args.frontend.resolve()
    if not frontend.is_relative_to((EVIDENCE/'builds').resolve()) or not (frontend/'index.html').is_file():
        parser.error('Use a versioned M10 build created by build_m10_preview.sh.')
    database=EVIDENCE/'clinrx-m10-preview.sqlite3'
    if not database.is_file():parser.error('Prepare the read-only patient backup before starting this preview.')
    from alembic import command
    from alembic.config import Config
    from app.persistence.database import create_database
    engine=create_database(database)
    try:
        with engine.begin() as connection:
            config=Config(str(ROOT/'backend/alembic.ini'));config.attributes['connection']=connection
            command.upgrade(config,'head')
    finally:engine.dispose()
    from app.demo.transfusion_gateway import SyntheticM10Gateway,retained_signing_key
    import uvicorn
    app=SyntheticM10Gateway(database,frontend,retained_signing_key(database),'http://127.0.0.1:5260')
    uvicorn.run(app,host='127.0.0.1',port=5260)

if __name__=='__main__':main()
