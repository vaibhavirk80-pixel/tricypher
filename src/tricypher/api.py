
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from .core import TriCypher
from .document_processor import (
    protect_document,
    restore_document,
    save_document,
    SUPPORTED_EXTENSIONS,
    MAX_FILE_SIZE,
)

app = FastAPI(
    title="TriCypher API",
    description="Local-first privacy protection layer for AI applications",
    version="0.3.0",
)

engine = TriCypher()


class ProtectRequest(BaseModel):
    text: str = Field(..., min_length=1)


class RestoreRequest(BaseModel):
    protected_text: str


class DocumentRestoreRequest(BaseModel):
    file_type: str
    protected_content: Any


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

        return {
            "protected_text": result["protected_text"],
            "detected_count": result["detected_count"],
            "detected_types": result["detected_types"],
            "token_map": result["token_map"],
        }

    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
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


@app.post("/v1/documents/protect")
async def protect_uploaded_document(
    file: UploadFile = File(...),
):
    temporary_path = None

    try:
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported document format",
            )

        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File exceeds the 10 MB size limit",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        result = protect_document(temporary_path, engine)

        result["filename"] = filename

        return result

    except HTTPException:
        raise

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Document protection failed",
        )

    finally:
        await file.close()

        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


@app.post("/v1/documents/restore")
def restore_uploaded_document(
    request: DocumentRestoreRequest,
):
    temporary_path = None

    try:
        extension = request.file_type.lower()

        if not extension.startswith("."):
            extension = "." + extension

        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported document format",
            )

        restored_content = restore_document(
            request.protected_content,
            extension,
            engine,
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        save_document(
            restored_content,
            extension,
            temporary_path,
        )

        media_types = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
        }

        return FileResponse(
            path=temporary_path,
            media_type=media_types[extension],
            filename=f"restored{extension}",
            background=BackgroundTask(
                os.unlink,
                str(temporary_path),
            ),
        )

    except HTTPException:
        raise

    except (ValueError, TypeError, KeyError) as error:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Document restoration failed",
        )
