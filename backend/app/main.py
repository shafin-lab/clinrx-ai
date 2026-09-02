from fastapi import FastAPI

from app.api.knowledge import router as knowledge_router

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


app.include_router(knowledge_router)