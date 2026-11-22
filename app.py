from fastapi import FastAPI

app = FastAPI(title="Skill & Knowledge Matchmaker")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
