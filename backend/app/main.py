from fastapi import FastAPI, HTTPException
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

@app.get("/knowledge/{knowledge_id}")
def get_knowledge_object(knowledge_id: str):

    knowledge_file = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "objects"
        / f"{knowledge_id}.json"
    )

    if not knowledge_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge Object '{knowledge_id}' not found."
        )

    with open(knowledge_file, "r") as file:
        return json.load(file)