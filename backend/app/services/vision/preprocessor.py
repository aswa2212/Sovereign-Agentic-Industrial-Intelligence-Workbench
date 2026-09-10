"""
SIH26117 — Deterministic Image Preprocessor
Applies contrast enhancement, grayscale normalization, and thresholding using Pillow.
Operates deterministically on byte buffers without overwriting original raw artifacts.
"""

import io
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.vision.base import InvalidImageError
except ImportError:
    from backend.app.services.vision.base import InvalidImageError


class PreprocessingConfig(BaseModel):
    """Configuration options for image enhancement pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    grayscale: bool = Field(default=True, description="Convert image to single-channel grayscale (L)")
    normalize_contrast: bool = Field(default=True, description="Apply autocontrast histogram stretching")
    contrast_factor: float = Field(default=1.3, description="Contrast multiplication factor (1.0 = neutral)")
    sharpen: bool = Field(default=True, description="Apply gentle edge sharpening filter for text clarity")
    binarize: bool = Field(default=False, description="Apply binary thresholding (pure black & white)")
    binary_threshold: int = Field(default=140, description="Pixel intensity threshold for binarization (0-255)")
    max_dimension: int = Field(default=2048, description="Maximum width or height; scales down if exceeded")
    output_format: str = Field(default="PNG", description="Output serialization format (PNG or JPEG)")


class ImagePreprocessor:
    """Deterministic image processing operations for OCR and Vision analysis."""

    def __init__(self, default_config: Optional[PreprocessingConfig] = None) -> None:
        self.config = default_config or PreprocessingConfig()

    def preprocess(
        self,
        image_bytes: bytes,
        config: Optional[PreprocessingConfig] = None,
    ) -> Tuple[bytes, Tuple[int, int]]:
        """
        Enhance image bytes according to configuration.
        Returns:
            Tuple[bytes, Tuple[int, int]]: (processed_image_bytes, (width, height))
        """
        cfg = config or self.config

        if not image_bytes:
            raise InvalidImageError("Cannot preprocess empty image buffer (0 bytes).")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert palette or RGBA with transparency cleanly
                if img.mode in ("P", "RGBA", "LA"):
                    # Create white background for alpha composite
                    canvas = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    canvas.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    current_img = canvas
                else:
                    current_img = img.convert("RGB")

                # 1. Grayscale
                if cfg.grayscale:
                    current_img = ImageOps.grayscale(current_img)

                # 2. Contrast Normalization / Autocontrast
                if cfg.normalize_contrast:
                    current_img = ImageOps.autocontrast(current_img, cutoff=1)

                # 3. Contrast Adjustment Factor
                if cfg.contrast_factor != 1.0:
                    enhancer = ImageEnhance.Contrast(current_img)
                    current_img = enhancer.enhance(cfg.contrast_factor)

                # 4. Sharpening
                if cfg.sharpen:
                    current_img = current_img.filter(ImageFilter.SHARPEN)

                # 5. Optional Binarization
                if cfg.binarize:
                    if current_img.mode != "L":
                        current_img = ImageOps.grayscale(current_img)
                    # Point thresholding
                    table = [0 if i < cfg.binary_threshold else 255 for i in range(256)]
                    current_img = current_img.point(table, mode="1")

                # 6. Scaling / Max Dimension constraint
                width, height = current_img.size
                if max(width, height) > cfg.max_dimension:
                    scale = cfg.max_dimension / max(width, height)
                    new_w = max(1, int(width * scale))
                    new_h = max(1, int(height * scale))
                    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                    current_img = current_img.resize((new_w, new_h), resample=resample)
                    width, height = new_w, new_h

                out_buf = io.BytesIO()
                # If mode is 1, save as PNG (JPEG doesn't support 1-bit)
                save_fmt = "PNG" if current_img.mode == "1" else cfg.output_format
                current_img.save(out_buf, format=save_fmt)
                return out_buf.getvalue(), (width, height)

        except Exception as e:
            if isinstance(e, InvalidImageError):
                raise
            raise InvalidImageError(
                f"Failed to process image bytes: {str(e)}"
            )
