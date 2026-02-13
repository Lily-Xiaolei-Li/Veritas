"""
Artifact Service for Agent B (B1.3).

Provides core functions for artifact management:
- Creating artifacts from tool/agent pipeline (internal use only)
- Streaming artifact content for downloads
- Generating previews for different file types
- Creating ZIP archives for batch downloads

Security:
- Path validation to prevent directory traversal
- Filename sanitization to block dangerous patterns
- No public API for arbitrary artifact creation
"""

import hashlib
import io
import mimetypes
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .logging_config import get_logger
from .models import Artifact

logger = get_logger("artifacts")

# Windows reserved filenames
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Characters not allowed in filenames
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# UUID pattern for validation
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

# Preview-able extensions by type
TEXT_EXTENSIONS = {"txt", "log", "csv", "xml", "html", "css", "ini", "cfg", "conf"}
CODE_EXTENSIONS = {"py", "js", "ts", "jsx", "tsx", "java", "c", "cpp", "h", "hpp", "go", "rs", "rb", "php", "sql", "sh", "bash", "zsh", "ps1", "bat", "cmd"}
MARKDOWN_EXTENSIONS = {"md", "markdown", "mdown", "mkd"}
JSON_EXTENSIONS = {"json", "jsonl", "geojson"}
YAML_EXTENSIONS = {"yaml", "yml"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "ico", "svg"}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    - Remove path separators (/ and backslash)
    - Block Windows reserved names (CON, NUL, etc.)
    - Remove null bytes and control characters
    - Limit length to 200 chars
    - Replace invalid chars with underscore

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for storage

    Raises:
        ValueError: If filename is empty or consists only of invalid chars
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove invalid characters
    filename = INVALID_FILENAME_CHARS.sub("_", filename)

    # Remove leading/trailing whitespace and dots
    filename = filename.strip().strip(".")

    # Check for Windows reserved names
    name_without_ext = filename.split(".")[0].upper()
    if name_without_ext in WINDOWS_RESERVED_NAMES:
        filename = f"_{filename}"

    # Limit length (preserve extension if possible)
    if len(filename) > 200:
        parts = filename.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 10:
            # Has extension, truncate name
            max_name_len = 200 - len(parts[1]) - 1
            filename = f"{parts[0][:max_name_len]}.{parts[1]}"
        else:
            filename = filename[:200]

    if not filename:
        raise ValueError("Filename is empty after sanitization")

    return filename


def validate_and_resolve_path(artifacts_dir: Path, relative_path: str) -> Path:
    """
    Validate artifact path is safe and resolve to absolute.

    Security checks:
    1. No .. traversal
    2. No absolute paths in input
    3. Resolved path must be under artifacts_dir
    4. Skip symlinks (don't follow)
    5. Sanitize Windows paths (backslash, drive letters)
    6. Block reserved names

    Args:
        artifacts_dir: Base directory for artifacts
        relative_path: Relative path to validate

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is invalid or unsafe
    """
    if not relative_path:
        raise ValueError("Path cannot be empty")

    # Reject obvious traversal attacks
    if ".." in relative_path:
        raise ValueError("Path traversal (..) not allowed")

    # Reject absolute paths
    if os.path.isabs(relative_path):
        raise ValueError("Absolute paths not allowed")

    # Normalize separators (Windows backslash to forward slash)
    normalized = relative_path.replace("\\", "/")

    # Check for Windows drive letters
    if len(normalized) >= 2 and normalized[1] == ":":
        raise ValueError("Windows drive letters not allowed")

    # Resolve and check containment
    artifacts_dir_resolved = artifacts_dir.resolve()
    resolved = (artifacts_dir / normalized).resolve()

    if not str(resolved).startswith(str(artifacts_dir_resolved)):
        raise ValueError("Path escapes artifacts directory")

    # Check for symlinks (reject) - only check if path exists
    if resolved.exists() and resolved.is_symlink():
        raise ValueError("Symlinks not allowed")

    return resolved


def get_storage_path(session_id: str, run_id: str, artifact_id: str, filename: str) -> str:
    """
    Generate deterministic storage path for an artifact.

    Format: {session_id}/{run_id}/{artifact_id}_{filename}

    Args:
        session_id: Session UUID
        run_id: Run UUID
        artifact_id: Artifact UUID
        filename: Sanitized filename

    Returns:
        Relative storage path
    """
    return f"{session_id}/{run_id}/{artifact_id}_{filename}"


def detect_mime_type(filename: str, content: Optional[bytes] = None) -> str:
    """
    Detect MIME type from filename and optionally content.

    Args:
        filename: Filename to detect from
        content: Optional file content for magic byte detection

    Returns:
        MIME type string (defaults to application/octet-stream)
    """
    # Try filename-based detection first
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        return mime_type

    # Fallback to magic byte detection if content provided
    if content and len(content) >= 4:
        # PNG
        if content[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        # JPEG
        if content[:2] == b'\xff\xd8':
            return "image/jpeg"
        # GIF
        if content[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        # PDF
        if content[:4] == b'%PDF':
            return "application/pdf"
        # ZIP
        if content[:4] == b'PK\x03\x04':
            return "application/zip"

    return "application/octet-stream"


def get_extension(filename: str) -> Optional[str]:
    """
    Extract extension from filename (without dot, lowercase).

    Args:
        filename: Filename to extract extension from

    Returns:
        Extension without dot, or None if no extension
    """
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext if ext else None


def get_preview_kind(extension: Optional[str], mime_type: Optional[str]) -> str:
    """
    Determine preview kind based on extension and MIME type.

    Args:
        extension: File extension (without dot)
        mime_type: MIME type string

    Returns:
        Preview kind: "text", "code", "markdown", "image", or "none"
    """
    if extension:
        ext_lower = extension.lower()
        if ext_lower in TEXT_EXTENSIONS:
            return "text"
        if ext_lower in CODE_EXTENSIONS:
            return "code"
        if ext_lower in MARKDOWN_EXTENSIONS:
            return "markdown"
        if ext_lower in JSON_EXTENSIONS or ext_lower in YAML_EXTENSIONS:
            return "code"
        if ext_lower in IMAGE_EXTENSIONS:
            return "image"

    # Fallback to MIME type
    if mime_type:
        if mime_type.startswith("text/"):
            return "text"
        if mime_type.startswith("image/"):
            return "image"
        if mime_type in ("application/json", "application/javascript"):
            return "code"

    return "none"


def can_preview(size_bytes: int, extension: Optional[str], mime_type: Optional[str]) -> bool:
    """
    Determine if artifact can be previewed.

    Args:
        size_bytes: File size in bytes
        extension: File extension
        mime_type: MIME type

    Returns:
        True if preview is supported
    """
    settings = get_settings()
    max_preview_bytes = settings.artifact_preview_max_kb * 1024

    # Images can preview even if large (we resize)
    preview_kind = get_preview_kind(extension, mime_type)
    if preview_kind == "image":
        return True

    # Text/code/markdown need size check
    if preview_kind in ("text", "code", "markdown"):
        return size_bytes <= max_preview_bytes * 10  # Allow 10x for text (we truncate)

    return False


def safe_text_preview(file_path: Path, max_bytes: int = 102400) -> Tuple[Optional[str], bool]:
    """
    Read text file safely with encoding detection.

    Args:
        file_path: Path to file
        max_bytes: Maximum bytes to read (default 100KB)

    Returns:
        Tuple of (text_content, is_truncated)
        Returns (None, False) if file appears binary
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read(max_bytes + 1)

        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]

        # Try UTF-8 first, fallback with replacement
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")

        # Check printable ratio - if too low, it's binary
        if len(text) > 0:
            printable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
            if printable / len(text) < 0.7:
                return None, False  # Treat as binary

        return text, truncated

    except Exception as e:
        logger.error(f"Failed to read file for preview: {e}")
        return None, False


async def create_artifact_internal(
    db_session: AsyncSession,
    run_id: str,
    session_id: str,
    filename: str,
    content: bytes,
    artifact_type: str = "file",
    artifact_meta: Optional[dict] = None,
) -> Artifact:
    """
    Create artifact from tool/agent pipeline (internal use only).

    Steps:
    1. Sanitize filename
    2. Generate deterministic storage path
    3. Validate path security
    4. Write to disk
    5. Compute SHA-256 hash
    6. Create DB record

    Args:
        db_session: Database session
        run_id: Run UUID
        session_id: Session UUID
        filename: Original filename
        content: File content as bytes
        artifact_type: Type of artifact (file, stdout, stderr, log)
        artifact_meta: Optional metadata dict

    Returns:
        Created Artifact model instance

    Raises:
        ValueError: If filename invalid or size exceeds limit
        IOError: If file write fails
    """
    settings = get_settings()

    # Validate size
    max_size_bytes = settings.max_artifact_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise ValueError(
            f"Artifact size ({len(content)} bytes) exceeds maximum "
            f"({max_size_bytes} bytes = {settings.max_artifact_size_mb} MB)"
        )

    # Sanitize filename
    safe_filename = sanitize_filename(filename)

    # Generate artifact ID and storage path
    artifact_id = str(uuid4())
    storage_path = get_storage_path(session_id, run_id, artifact_id, safe_filename)

    # Validate and resolve full path
    artifacts_dir = Path(settings.artifacts_dir)
    full_path = validate_and_resolve_path(artifacts_dir, storage_path)

    # Ensure parent directories exist
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute hash
    content_hash = hashlib.sha256(content).hexdigest()

    # Detect MIME type and extension
    mime_type = detect_mime_type(safe_filename, content)
    extension = get_extension(safe_filename)

    # Write to disk
    try:
        with open(full_path, "wb") as f:
            f.write(content)
        logger.info(
            f"Artifact written to disk: {storage_path}",
            extra={"extra_fields": {"artifact_id": artifact_id, "size": len(content)}}
        )
    except Exception as e:
        logger.error(f"Failed to write artifact to disk: {e}")
        raise IOError(f"Failed to write artifact: {e}") from e

    # Create database record
    artifact = Artifact(
        id=artifact_id,
        run_id=run_id,
        session_id=session_id,
        display_name=filename,  # Keep original name for display
        storage_path=storage_path,
        extension=extension,
        size_bytes=len(content),
        content_hash=content_hash,
        mime_type=mime_type,
        artifact_type=artifact_type,
        artifact_meta=artifact_meta,
    )

    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    logger.info(
        f"Artifact created: {artifact_id}",
        extra={
            "extra_fields": {
                "artifact_id": artifact_id,
                "run_id": run_id,
                "session_id": session_id,
                "filename": safe_filename,
                "size_bytes": len(content),
            }
        }
    )

    return artifact


async def get_artifact_content_stream(
    artifact: Artifact,
    chunk_size: int = 65536
) -> AsyncGenerator[bytes, None]:
    """
    Stream artifact content from filesystem in chunks.

    Args:
        artifact: Artifact model instance
        chunk_size: Size of each chunk (default 64KB)

    Yields:
        Chunks of file content

    Raises:
        FileNotFoundError: If artifact file not found on disk
    """
    settings = get_settings()
    artifacts_dir = Path(settings.artifacts_dir)
    full_path = artifacts_dir / artifact.storage_path

    if not full_path.exists():
        logger.error(
            f"Artifact file not found on disk: {artifact.storage_path}",
            extra={"extra_fields": {"artifact_id": artifact.id}}
        )
        raise FileNotFoundError(
            f"Artifact file not found. The file may have been moved or deleted. "
            f"Artifact ID: {artifact.id}, Expected path: {artifact.storage_path}"
        )

    try:
        with open(full_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.error(f"Failed to stream artifact content: {e}")
        raise


def get_artifact_preview(artifact: Artifact) -> dict:
    """
    Generate preview for artifact based on type.

    Args:
        artifact: Artifact model instance

    Returns:
        Preview dict with kind, content_type, truncated, text fields
    """
    settings = get_settings()
    artifacts_dir = Path(settings.artifacts_dir)
    full_path = artifacts_dir / artifact.storage_path

    preview_kind = get_preview_kind(artifact.extension, artifact.mime_type)
    max_preview_bytes = settings.artifact_preview_max_kb * 1024

    result = {
        "kind": preview_kind,
        "content_type": artifact.mime_type or "application/octet-stream",
        "truncated": False,
        "text": None,
    }

    if not full_path.exists():
        result["kind"] = "none"
        result["text"] = "File not found on disk"
        return result

    # Size check for non-image types
    if preview_kind in ("text", "code", "markdown"):
        text, truncated = safe_text_preview(full_path, max_preview_bytes)
        if text is None:
            result["kind"] = "none"
        else:
            result["text"] = text
            result["truncated"] = truncated

    # For images, we return "image" kind - actual image served separately
    # The frontend will use the preview endpoint with Accept header

    return result


async def create_zip_stream(
    artifacts: List[Artifact],
    chunk_size: int = 65536
) -> AsyncGenerator[bytes, None]:
    """
    Stream ZIP file containing artifacts without buffering entire file.

    Uses in-memory buffer with periodic flushing for streaming.

    Args:
        artifacts: List of Artifact model instances
        chunk_size: Size of each yielded chunk

    Yields:
        Chunks of ZIP file content
    """
    settings = get_settings()
    artifacts_dir = Path(settings.artifacts_dir)

    # Use BytesIO as buffer for ZipFile
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for artifact in artifacts:
            if artifact.is_deleted:
                continue

            full_path = artifacts_dir / artifact.storage_path

            if not full_path.exists():
                logger.warning(
                    f"Skipping missing artifact in ZIP: {artifact.storage_path}",
                    extra={"extra_fields": {"artifact_id": artifact.id}}
                )
                continue

            # Use display_name for the filename in ZIP
            # Prefix with run_id to avoid collisions
            zip_filename = f"{artifact.run_id}/{artifact.display_name}"

            try:
                zf.write(full_path, zip_filename)
            except Exception as e:
                logger.error(f"Failed to add artifact to ZIP: {e}")
                continue

    # Get the complete ZIP content
    buffer.seek(0)

    # Yield in chunks
    while True:
        chunk = buffer.read(chunk_size)
        if not chunk:
            break
        yield chunk


async def soft_delete_artifact(
    db_session: AsyncSession,
    artifact: Artifact
) -> None:
    """
    Soft-delete an artifact (set is_deleted=True).

    Args:
        db_session: Database session
        artifact: Artifact to delete
    """
    artifact.is_deleted = True
    await db_session.commit()

    logger.info(
        f"Artifact soft-deleted: {artifact.id}",
        extra={"extra_fields": {"artifact_id": artifact.id}}
    )
