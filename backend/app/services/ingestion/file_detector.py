"""
SIH26117 — Content-Aware File Type & MIME Detector
Inspects file magic bytes, content signatures, and extensions portably.
Operates without external system binaries (libmagic) or OS registry keys.
"""

import io
import zipfile
from pathlib import Path
from typing import Optional, Tuple

try:
    from app.services.ingestion.exceptions import (
        InvalidDocumentError,
        UnsupportedFileTypeError,
    )
    from app.services.ingestion.models import MediaType
except ImportError:
    from backend.app.services.ingestion.exceptions import (
        InvalidDocumentError,
        UnsupportedFileTypeError,
    )
    from backend.app.services.ingestion.models import MediaType

# Magic signatures
MAGIC_PDF = b"%PDF-"
MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_JPEG = b"\xff\xd8\xff"
MAGIC_ZIP = b"PK\x03\x04"

# Disallowed dangerous extensions
DANGEROUS_EXTENSIONS = {
    "exe", "dll", "bat", "cmd", "sh", "vbs", "ps1", "com", "scr", "pif", "jar", "py"
}

# Mapping of canonical extensions to MediaType
EXTENSION_TO_MEDIA_TYPE = {
    "pdf": MediaType.PDF.value,
    "docx": MediaType.DOCX.value,
    "xlsx": MediaType.XLSX.value,
    "csv": MediaType.CSV.value,
    "png": MediaType.PNG.value,
    "jpg": MediaType.JPEG.value,
    "jpeg": MediaType.JPEG.value,
}


def detect_file_type(
    content: bytes,
    filename: str,
) -> Tuple[str, str]:
    """
    Detect media type and normalized extension from raw bytes and filename.
    
    Returns:
        Tuple[str, str]: (media_type, extension)
    
    Raises:
        UnsupportedFileTypeError: If file type is unsupported or dangerous.
        InvalidDocumentError: If magic bytes contradict file extension.
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    # Reject dangerous executable formats
    if ext in DANGEROUS_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"File extension '{ext}' is dangerous and not allowed.",
            details={"filename": filename, "extension": ext},
        )

    if not ext:
        raise UnsupportedFileTypeError(
            "Missing file extension. Cannot determine document format.",
            details={"filename": filename},
        )

    if ext not in EXTENSION_TO_MEDIA_TYPE:
        raise UnsupportedFileTypeError(
            f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, XLSX, CSV, PNG, JPG/JPEG.",
            details={"filename": filename, "extension": ext},
        )

    # 1. PDF Verification
    if ext == "pdf":
        if not content.startswith(MAGIC_PDF):
            # Check within first 1024 bytes (some PDFs have leading whitespace/comments)
            if MAGIC_PDF not in content[:1024]:
                raise InvalidDocumentError(
                    "Invalid PDF file: Missing '%PDF-' header signature.",
                    details={"filename": filename, "detected_header": content[:16].hex()},
                )
        return MediaType.PDF.value, "pdf"

    # 2. PNG Verification
    if ext == "png":
        if not content.startswith(MAGIC_PNG):
            raise InvalidDocumentError(
                "Invalid PNG file: Missing standard PNG header signature.",
                details={"filename": filename, "detected_header": content[:8].hex()},
            )
        return MediaType.PNG.value, "png"

    # 3. JPEG Verification
    if ext in ("jpg", "jpeg"):
        if not content.startswith(MAGIC_JPEG):
            raise InvalidDocumentError(
                "Invalid JPEG file: Missing standard JPEG SOI marker.",
                details={"filename": filename, "detected_header": content[:4].hex()},
            )
        return MediaType.JPEG.value, "jpg"

    # 4. DOCX / XLSX (Office Open XML - Zip container verification)
    if ext in ("docx", "xlsx"):
        if not content.startswith(MAGIC_ZIP):
            raise InvalidDocumentError(
                f"Invalid {ext.upper()} file: Expected ZIP container magic signature.",
                details={"filename": filename, "detected_header": content[:4].hex()},
            )
        # Inspect internal ZIP catalog to differentiate docx from xlsx
        try:
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                namelist = zf.namelist()
                if ext == "docx":
                    if not any(name.startswith("word/") for name in namelist):
                        raise InvalidDocumentError(
                            "Invalid DOCX file: Missing 'word/' directory in Office Open XML container.",
                            details={"filename": filename},
                        )
                    return MediaType.DOCX.value, "docx"
                elif ext == "xlsx":
                    if not any(name.startswith("xl/") for name in namelist):
                        raise InvalidDocumentError(
                            "Invalid XLSX file: Missing 'xl/' directory in Office Open XML container.",
                            details={"filename": filename},
                        )
                    return MediaType.XLSX.value, "xlsx"
        except zipfile.BadZipFile as e:
            raise InvalidDocumentError(
                f"Corrupted or invalid {ext.upper()} archive: {str(e)}",
                details={"filename": filename},
            )

    # 5. CSV Verification
    if ext == "csv":
        # Ensure content is decodable text
        is_text = False
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                content[:4096].decode(encoding)
                is_text = True
                break
            except UnicodeDecodeError:
                continue

        if not is_text:
            raise InvalidDocumentError(
                "Invalid CSV file: Binary data detected; cannot decode as text.",
                details={"filename": filename},
            )
        return MediaType.CSV.value, "csv"

    # Fallback to mapped media type
    return EXTENSION_TO_MEDIA_TYPE[ext], ext
