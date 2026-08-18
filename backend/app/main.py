from fastapi import FastAPI
from pathlib import Path
import json

app = FastAPI(
    title="ClinRx AI",
    version="0.0.1"
)


@app.get("/")
def root():
    return {
        "application": "ClinRx AI",
        "version": "0.0.1",
        "status": "running"
    }


@app.get("/knowledge")
def get_knowledge():

    knowledge_dir = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "objects"
    )

    knowledge_objects = []

    for json_file in sorted(knowledge_dir.glob("*.json")):
        with open(json_file, "r") as file:
            knowledge_objects.append(json.load(file))

    return knowledge_objects