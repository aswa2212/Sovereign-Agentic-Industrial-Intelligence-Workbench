"""
SIH26117 — Streaming SHA-256 Hasher Module
Computes cryptographic SHA-256 checksums over raw file streams and byte buffers.
Ensures memory-efficient chunked computation for large industrial artifacts.
"""

import hashlib
from pathlib import Path
from typing import BinaryIO, Union

DEFAULT_CHUNK_SIZE = 65536  # 64 KB chunks


def compute_sha256_bytes(data: bytes) -> str:
    """
    Compute SHA-256 hexadecimal digest directly from an in-memory byte sequence.
    """
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def compute_sha256_stream(stream: BinaryIO, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """
    Compute SHA-256 hexadecimal digest from an open binary file-like stream
    by reading incrementally in chunks to prevent memory exhaustion.
    Preserves the initial stream seek position.
    """
    hasher = hashlib.sha256()
    start_pos = 0
    if hasattr(stream, "tell") and hasattr(stream, "seek"):
        try:
            start_pos = stream.tell()
        except (OSError, ValueError):
            start_pos = 0

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)

    if hasattr(stream, "seek"):
        try:
            stream.seek(start_pos)
        except (OSError, ValueError):
            pass

    return hasher.hexdigest()


def compute_sha256_file(file_path: Union[str, Path], chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """
    Compute SHA-256 hexadecimal digest of a local filesystem file using chunked streaming.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for SHA-256 hashing: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)

    return hasher.hexdigest()
