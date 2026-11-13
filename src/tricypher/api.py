
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .core import TriCypher

app = FastAPI(
    title="TriCypher API",
    description="Local-first privacy protection layer for AI applications",
    version="0.2.0",
)

engine = TriCypher()


class ProtectRequest(BaseModel):
    text: str = Field(..., min_length=1)


class RestoreRequest(BaseModel):
    protected_text: str


@app.get("/")
def home():
    return {
        "message": "Welcome to TriCypher API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "engine": "TriCypher",
    }


@app.post("/v1/protect")
def protect(request: ProtectRequest):
    try:
        result = engine.protect(request.text)

        # Return sanitized content and metadata only.
        return {
            "protected_text": result["protected_text"],
            "detected_count": result["detected_count"],
            "detected_types": result["detected_types"],
            "token_map": result["token_map"],
        }

    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        # Never expose original input or internal exception details.
        raise HTTPException(
            status_code=500,
            detail="Local protection failed. Prompt was not protected.",
        )


@app.post("/v1/restore")
def restore(request: RestoreRequest):
    try:
        restored = engine.restore(request.protected_text)

        return {
            "restored_text": restored,
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Restoration failed",
        )
