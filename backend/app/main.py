from fastapi import FastAPI

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