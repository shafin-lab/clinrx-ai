from pathlib import Path
import json


KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[3]
    / "knowledge"
    / "objects"
)


def get_all_knowledge():

    knowledge_objects = []

    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        with open(json_file, "r") as file:
            knowledge_objects.append(json.load(file))

    return knowledge_objects


def get_knowledge_by_id(knowledge_id: str):

    knowledge_file = KNOWLEDGE_DIR / f"{knowledge_id}.json"

    if not knowledge_file.exists():
        return None

    with open(knowledge_file, "r") as file:
        return json.load(file)