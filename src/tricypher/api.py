
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .core import TriCypher

app = FastAPI(
    title="TriCypher API",
    description="Privacy protection layer for AI applications",
    version="0.1.0",
)

engine = TriCypher()

class ProtectRequest(BaseModel):
    text: str

class RestoreRequest(BaseModel):
    protected_text: str

@app.get("/")
def home():
    return {
        "message": "Welcome to TriCypher API",
        "status": "running",
    }

@app.post("/v1/protect")
def protect(request: ProtectRequest):
    try:
        return engine.protect(request.text)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))

@app.post("/v1/restore")
def restore(request: RestoreRequest):
    try:
        restored = engine.restore(request.protected_text)
        return {"restored_text": restored}
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Restoration failed",
        )