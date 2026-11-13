
import csv
import json
import textwrap
import shutil
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Find Tesseract automatically.
TESSERACT_PATH = shutil.which("tesseract")

# Windows fallback location.
if not TESSERACT_PATH:
    default_path = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if default_path.exists():
        TESSERACT_PATH = str(default_path)

if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ---------------------------------------------------------
# FILE VALIDATION
# ---------------------------------------------------------

def _validate_file(file_path: str | Path) -> Path:
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")

    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 10 MB size limit")

    return path


# ---------------------------------------------------------
# IMAGE OCR
# ---------------------------------------------------------

def _extract_image_text(path: Path) -> str:
    """Extract text from PNG, JPG or JPEG using Tesseract OCR."""

    if not TESSERACT_PATH:
        raise RuntimeError(
            "Tesseract OCR was not found. "
            "Install Tesseract or configure its executable path."
        )

    try:
        with Image.open(path) as image:
            # Correct image orientation using EXIF metadata.
            image = ImageOps.exif_transpose(image)

            # Convert to a format suitable for OCR.
            image = image.convert("RGB")

            extracted_text = pytesseract.image_to_string(
                image,
                lang="eng",
            )

    except pytesseract.TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract executable could not be started. "
            "Check the Tesseract installation and PATH."
        ) from error

    except Exception as error:
        raise ValueError(
            f"Unable to read image or extract its text: {error}"
        ) from error

    return extracted_text


# ---------------------------------------------------------
# TEXT EXTRACTION
# ---------------------------------------------------------

def extract_text(file_path: str | Path) -> dict:
    """Extract text from supported document formats."""

    path = _validate_file(file_path)
    extension = path.suffix.lower()

    # PDF
    if extension == ".pdf":

        text_parts = []

        with pymupdf.open(path) as document:

            for page_number, page in enumerate(
                document,
                start=1,
            ):
                page_text = page.get_text()

                if page_text.strip():
                    text_parts.append(
                        f"[Page {page_number}]\n{page_text}"
                    )

        extracted_text = "\n".join(text_parts)

    # PNG, JPG, JPEG
    elif extension in {".png", ".jpg", ".jpeg"}:

        extracted_text = _extract_image_text(path)

    # JSON
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

    # CSV
    elif extension == ".csv":

        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            rows = csv.reader(file)

            extracted_text = "\n".join(
                " | ".join(row)
                for row in rows
            )

    # TXT AND MARKDOWN
    else:

        extracted_text = path.read_text(
            encoding="utf-8-sig"
        )

    return {
        "filename": path.name,
        "file_type": extension,
        "text": extracted_text,
        "character_count": len(extracted_text),
        "empty": not extracted_text.strip(),
    }


# ---------------------------------------------------------
# DETECTION STATISTICS
# ---------------------------------------------------------

def _update_stats(result: dict, stats: dict) -> None:
    """Accumulate detection statistics."""

    stats["detected_count"] += result["detected_count"]

    for entity_type in result["detected_types"]:

        if entity_type not in stats["detected_types"]:
            stats["detected_types"].append(entity_type)

    stats["token_map"].update(result["token_map"])


# ---------------------------------------------------------
# CONTEXT-AWARE NAME PROTECTION
# ---------------------------------------------------------

def _protect_name_with_context(
    value: str,
    engine,
    stats: dict,
) -> str:
    """Protect a name using temporary detection context."""

    if not value.strip():
        return value

    prefix = "Applicant "

    result = engine.protect(prefix + value)

    _update_stats(result, stats)

    # Correct vault values if the entire phrase was tokenized.
    for token in result["token_map"]:

        original = engine.vault.restore(token)

        if original is not None and original.startswith(prefix):

            engine.vault.store(
                original[len(prefix):],
                token=token,
            )

    protected_text = result["protected_text"]

    if protected_text.startswith(prefix):
        protected_text = protected_text[len(prefix):]

    return protected_text


# ---------------------------------------------------------
# NORMAL STRING PROTECTION
# ---------------------------------------------------------

def _protect_string(
    value: str,
    engine,
    stats: dict,
) -> str:
    """Protect a string and accumulate detection metadata."""

    if not isinstance(value, str):
        return value

    if not value.strip():
        return value

    result = engine.protect(value)

    _update_stats(result, stats)

    return result["protected_text"]


# ---------------------------------------------------------
# JSON FIELD NORMALIZATION
# ---------------------------------------------------------

def _normalize_field_name(field_name) -> str:
    """Normalize JSON keys and CSV headers."""

    if field_name is None:
        return ""

    return (
        str(field_name)
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


NAME_FIELDS = {
    "name",
    "fullname",
    "applicantname",
    "employeename",
    "customername",
    "patientname",
    "beneficiaryname",
    "vendorname",
    "suppliername",
    "guardianname",
    "fathername",
    "mothername",
    "spousename",
}


# ---------------------------------------------------------
# JSON PROTECTION
# ---------------------------------------------------------

def _protect_json(
    value,
    engine,
    stats,
    field_name=None,
):
    """Protect JSON strings recursively."""

    if isinstance(value, str):

        normalized_field = _normalize_field_name(field_name)

        if normalized_field in NAME_FIELDS:

            return _protect_name_with_context(
                value,
                engine,
                stats,
            )

        return _protect_string(
            value,
            engine,
            stats,
        )

    if isinstance(value, dict):

        return {
            key: _protect_json(
                item,
                engine,
                stats,
                field_name=key,
            )
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            _protect_json(
                item,
                engine,
                stats,
                field_name=field_name,
            )
            for item in value
        ]

    return value


# ---------------------------------------------------------
# JSON RESTORATION
# ---------------------------------------------------------

def _restore_json(value, engine):
    """Restore JSON strings recursively."""

    if isinstance(value, str):
        return engine.restore(value)

    if isinstance(value, dict):

        return {
            key: _restore_json(item, engine)
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            _restore_json(item, engine)
            for item in value
        ]

    return value


# ---------------------------------------------------------
# CSV READING
# ---------------------------------------------------------

def _read_csv(path: Path):
    """Read CSV rows and retain basic dialect information."""

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        sample = file.read(8192)
        file.seek(0)

        try:

            dialect = csv.Sniffer().sniff(
                sample,
                delimiters=",;\t|",
            )

        except csv.Error:
            dialect = csv.excel

        rows = list(csv.reader(file, dialect))

    dialect_info = {
        "delimiter": dialect.delimiter,
        "quotechar": dialect.quotechar,
        "doublequote": dialect.doublequote,
        "escapechar": dialect.escapechar,
        "quoting": dialect.quoting,
        "skipinitialspace": dialect.skipinitialspace,
    }

    return rows, dialect_info


# ---------------------------------------------------------
# CSV PROTECTION
# ---------------------------------------------------------

def _protect_csv(
    path: Path,
    engine,
    stats: dict,
) -> dict:
    """Protect CSV values while preserving structure."""

    rows, dialect_info = _read_csv(path)

    if not rows:

        return {
            "rows": [],
            "dialect": dialect_info,
        }

    headers = rows[0]

    protected_rows = [headers.copy()]

    for row in rows[1:]:

        protected_row = []

        for index, cell in enumerate(row):

            header = (
                _normalize_field_name(headers[index])
                if index < len(headers)
                else ""
            )

            if header in NAME_FIELDS and cell.strip():

                protected_cell = _protect_name_with_context(
                    cell,
                    engine,
                    stats,
                )

            else:

                protected_cell = _protect_string(
                    cell,
                    engine,
                    stats,
                )

            protected_row.append(protected_cell)

        protected_rows.append(protected_row)

    return {
        "rows": protected_rows,
        "dialect": dialect_info,
    }


# ---------------------------------------------------------
# DOCUMENT PROTECTION
# ---------------------------------------------------------

def protect_document(
    file_path: str | Path,
    engine,
) -> dict:
    """Protect supported documents using the local engine."""

    path = _validate_file(file_path)
    extension = path.suffix.lower()

    stats = {
        "detected_count": 0,
        "detected_types": [],
        "token_map": {},
    }

    # TXT AND MARKDOWN
    if extension in {".txt", ".md"}:

        original = path.read_text(
            encoding="utf-8-sig"
        )

        protected = _protect_string(
            original,
            engine,
            stats,
        )

    # JSON
    elif extension == ".json":

        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:

            original = json.load(file)

        protected = _protect_json(
            original,
            engine,
            stats,
        )

    # CSV
    elif extension == ".csv":

        protected = _protect_csv(
            path,
            engine,
            stats,
        )

    # PDF
    elif extension == ".pdf":

        pages = []
        page_sizes = []

        with pymupdf.open(path) as document:

            for page in document:

                page_text = page.get_text()

                protected_page = _protect_string(
                    page_text,
                    engine,
                    stats,
                )

                pages.append(protected_page)

                page_sizes.append([
                    page.rect.width,
                    page.rect.height,
                ])

        protected = {
            "pages": pages,
            "page_sizes": page_sizes,
        }

    # IMAGE FILES
    elif extension in {".png", ".jpg", ".jpeg"}:

        extracted = extract_text(path)

        if not extracted["text"].strip():

            raise ValueError(
                "No readable text found in the image. "
                "Please check the image quality."
            )

        # OCR text is protected using the existing engine.
        protected = _protect_string(
            extracted["text"],
            engine,
            stats,
        )

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    is_image = extension in {
        ".png",
        ".jpg",
        ".jpeg",
    }

    # Image OCR output is treated as a TXT document.
    output_file_type = ".txt" if is_image else extension

    output_filename = (
        path.stem + ".txt"
        if is_image
        else path.name
    )

    return {
        "filename": output_filename,
        "original_filename": path.name,
        "file_type": output_file_type,
        "source_file_type": extension,
        "protected_content": protected,
        "detected_count": stats["detected_count"],
        "detected_types": stats["detected_types"],
        "token_map": stats["token_map"],
    }


# ---------------------------------------------------------
# DOCUMENT RESTORATION
# ---------------------------------------------------------

def restore_document(
    protected_content,
    file_type: str,
    engine,
):
    """Restore protected content using the local token vault."""

    extension = file_type.lower()

    if not extension.startswith("."):
        extension = "." + extension

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    # TXT AND MARKDOWN
    if extension in {".txt", ".md"}:

        if not isinstance(protected_content, str):

            raise TypeError(
                "Text document content must be a string"
            )

        return engine.restore(protected_content)

    # JSON
    if extension == ".json":

        return _restore_json(
            protected_content,
            engine,
        )

    # CSV
    if extension == ".csv":

        if not isinstance(protected_content, dict):

            raise TypeError(
                "Invalid CSV document content"
            )

        if "rows" not in protected_content:

            raise ValueError(
                "CSV content is missing rows"
            )

        return {
            "rows": [
                [
                    engine.restore(cell)
                    for cell in row
                ]
                for row in protected_content["rows"]
            ],
            "dialect": protected_content["dialect"],
        }

    # PDF
    if extension == ".pdf":

        if not isinstance(protected_content, dict):

            raise TypeError(
                "Invalid PDF document content"
            )

        return {
            "pages": [
                engine.restore(page)
                for page in protected_content["pages"]
            ],
            "page_sizes": protected_content["page_sizes"],
        }

    raise ValueError(
        f"Unsupported file type: {extension}"
    )


# ---------------------------------------------------------
# RESTORED DOCUMENT SAVING
# ---------------------------------------------------------

def save_document(
    content,
    file_type: str,
    output_path: str | Path,
):
    """Save restored or protected content."""

    extension = file_type.lower()

    if not extension.startswith("."):
        extension = "." + extension

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    path = Path(output_path)

    if path.suffix.lower() != extension:

        raise ValueError(
            "Output filename extension does not match file type"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # TXT AND MARKDOWN
    if extension in {".txt", ".md"}:

        if not isinstance(content, str):
            raise TypeError("Text content must be a string")

        path.write_text(
            content,
            encoding="utf-8",
        )

    # JSON
    elif extension == ".json":

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                content,
                file,
                ensure_ascii=False,
                indent=2,
            )

    # CSV
    elif extension == ".csv":

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:

            dialect = content["dialect"]

            writer = csv.writer(
                file,
                delimiter=dialect["delimiter"],
                quotechar=dialect["quotechar"],
                doublequote=dialect["doublequote"],
                escapechar=dialect["escapechar"],
                quoting=dialect["quoting"],
                skipinitialspace=dialect["skipinitialspace"],
            )

            writer.writerows(content["rows"])

    # PDF
    elif extension == ".pdf":

        pages = content["pages"]
        page_sizes = content["page_sizes"]

        if len(pages) != len(page_sizes):

            raise ValueError(
                "PDF page content and dimensions do not match"
            )

        output = pymupdf.open()

        try:

            for page_text, dimensions in zip(
                pages,
                page_sizes,
            ):

                width, height = dimensions

                if width <= 0 or height <= 0:

                    raise ValueError(
                        "Invalid PDF page dimensions"
                    )

                max_width = width - 72
                max_height = height - 72

                font_size = 9
                line_height = 12

                char_width = max(
                    20,
                    int(max_width / 5),
                )

                wrapped_lines = []

                for line in page_text.splitlines():

                    wrapped_lines.extend(
                        textwrap.wrap(
                            line,
                            width=char_width,
                            replace_whitespace=False,
                            drop_whitespace=False,
                        ) or [""]
                    )

                if not wrapped_lines:
                    wrapped_lines = [""]

                lines_per_page = max(
                    1,
                    int(max_height / line_height),
                )

                chunks = [
                    wrapped_lines[index:index + lines_per_page]
                    for index in range(
                        0,
                        len(wrapped_lines),
                        lines_per_page,
                    )
                ]

                for chunk in chunks:

                    page = output.new_page(
                        width=width,
                        height=height,
                    )

                    y = 36 + font_size

                    for line in chunk:

                        page.insert_text(
                            (36, y),
                            line,
                            fontsize=font_size,
                            fontname="helv",
                        )

                        y += line_height

            output.save(path)

        finally:
            output.close()

    return {
        "filename": path.name,
        "file_type": extension,
        "saved": True,
    }
