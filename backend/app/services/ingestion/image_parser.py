"""
SIH26117 — Image Ingestion Parser Module
Validates PNG and JPEG images using Pillow.
Extracts geometry, color mode, and channel metadata without executing OCR or Vision inference.
"""

import io
from typing import Any, Dict, Tuple
from PIL import Image

try:
    from app.services.ingestion.exceptions import InvalidDocumentError
    from app.services.ingestion.models import DocumentProvenance, ImageInfo
except ImportError:
    from backend.app.services.ingestion.exceptions import InvalidDocumentError
    from backend.app.services.ingestion.models import DocumentProvenance, ImageInfo


class ImageParser:
    """Validates and extracts structural properties of uploaded technical images."""

    def parse(
        self,
        content: bytes,
        sha256: str,
        filename: str,
    ) -> Tuple[ImageInfo, Dict[str, Any]]:
        """
        Parse raw image bytes and extract dimensional metadata.
        Does NOT perform OCR or VLM inference.

        Returns:
            Tuple[ImageInfo, Dict[str, Any]]
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                img_format = img.format or "UNKNOWN"
                width, height = img.size
                mode = img.mode
                
                # Check for alpha channel
                has_alpha = "A" in mode or mode in ("RGBA", "LA")
                
                # Channel count
                channel_count = len(img.getbands()) if hasattr(img, "getbands") else 3

                metadata = {
                    "format": img_format,
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "channels": channel_count,
                    "has_alpha": has_alpha,
                }

                provenance = DocumentProvenance(
                    source_filename=filename,
                    source_sha256=sha256,
                )

                image_info = ImageInfo(
                    format=img_format,
                    width=width,
                    height=height,
                    mode=mode,
                    color_channels=channel_count,
                    has_alpha=has_alpha,
                    size_bytes=len(content),
                    provenance=provenance,
                )

                return image_info, metadata

        except Exception as e:
            raise InvalidDocumentError(
                f"Failed to decode image: {str(e)}",
                details={"filename": filename},
            )
