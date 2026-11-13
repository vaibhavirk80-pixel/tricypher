
import csv
import json
from pathlib import Path

import pymupdf

SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def extract_text(file_path: str | Path) -> dict:
    """
    Extract text from supported document formats.
    Returns extracted text and basic file metadata.
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 10 MB size limit")

    extension = path.suffix.lower()

    if extension == ".pdf":
        text_parts = []

        with pymupdf.open(path) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(
                        f"[Page {page_number}]\n{page_text}"
                    )

        extracted_text = "\n".join(text_parts)

    elif extension == ".json":
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        def collect_strings(value):
            if isinstance(value, str):
                return [value]
            if isinstance(value, dict):
                return [
                    text
                    for item in value.values()
                    for text in collect_strings(item)
                ]
            if isinstance(value, list):
                return [
                    text
                    for item in value
                    for text in collect_strings(item)
                ]
            return []

        extracted_text = "\n".join(collect_strings(data))

    elif extension == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            extracted_text = "\n".join(
                " | ".join(row) for row in rows
            )

    else:
        extracted_text = path.read_text(encoding="utf-8-sig")

    return {
        "filename": path.name,
        "file_type": extension,
        "text": extracted_text,
        "character_count": len(extracted_text),
        "empty": not extracted_text.strip(),
    }