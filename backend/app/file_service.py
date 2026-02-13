"""
File Service for Agent B (B1.2).

Provides file indexing utilities including:
- Path validation and security checks
- File hashing (SHA-256)
- File metadata extraction
"""

import hashlib
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .logging_config import get_logger
from .models import FileIndex

logger = get_logger("file_service")

# Thread pool for hash computation (avoid blocking event loop)
_hash_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="file_hash_")


class PathSecurityError(Exception):
    """Raised when a path fails security validation."""
    pass


def validate_path_safety(workspace_root: Path, rel_path: str) -> Path:
    """
    Validate that a path is safe and within workspace bounds.

    MUST be called on indexing AND on any file read/access.

    Args:
        workspace_root: The workspace root directory (absolute path)
        rel_path: Relative path to validate

    Returns:
        Resolved absolute path if valid

    Raises:
        PathSecurityError: If path escapes workspace or is a symlink
    """
    # Normalize and resolve
    workspace_resolved = workspace_root.resolve()
    target = (workspace_root / rel_path).resolve()

    # Check: must be inside workspace (blocks ../ traversal)
    if not target.is_relative_to(workspace_resolved):
        raise PathSecurityError(f"Path escape attempt blocked: {rel_path}")

    # Check: must not be a symlink (blocks symlink escape)
    if target.is_symlink():
        raise PathSecurityError(f"Symlinks not allowed: {rel_path}")

    return target


def get_relative_path(workspace_root: Path, absolute_path: Path) -> str:
    """
    Get the relative path from workspace root.

    Args:
        workspace_root: The workspace root directory
        absolute_path: Absolute path to convert

    Returns:
        Relative path as string (forward slashes for consistency)
    """
    rel = absolute_path.relative_to(workspace_root.resolve())
    # Use forward slashes for consistency across platforms
    return str(rel).replace("\\", "/")


def compute_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file (synchronous, for use in threadpool).

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read

    Returns:
        Hex digest of SHA-256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


async def compute_file_hash_async(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file asynchronously (uses threadpool).

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read

    Returns:
        Hex digest of SHA-256 hash
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _hash_executor, compute_file_hash, file_path, chunk_size
    )


def extract_file_metadata(
    workspace_root: Path,
    file_path: Path,
    max_size_mb: int = 100,
) -> dict:
    """
    Extract metadata from a file for indexing.

    Args:
        workspace_root: The workspace root directory
        file_path: Absolute path to the file
        max_size_mb: Maximum file size in MB to compute hash

    Returns:
        Dictionary with file metadata ready for FileIndex creation
    """
    rel_path = get_relative_path(workspace_root, file_path)
    stat = file_path.stat()
    filename = file_path.name

    # Extract extension (without dot)
    extension = file_path.suffix.lstrip(".").lower() if file_path.suffix else None

    # Get parent directory (relative path)
    parent_dir = str(file_path.parent.relative_to(workspace_root.resolve())).replace(
        "\\", "/"
    )
    if parent_dir == ".":
        parent_dir = ""

    # Guess MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))

    # File size
    size_bytes = stat.st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    # Only compute hash for files under size limit
    content_hash = None
    if size_bytes <= max_size_bytes:
        try:
            content_hash = compute_file_hash(file_path)
        except Exception as e:
            logger.warning(
                f"Failed to compute hash for {rel_path}: {e}",
                extra={"extra_fields": {"path": rel_path, "error": str(e)}},
            )

    # Get modification time
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    return {
        "id": str(uuid4()),
        "path": rel_path,
        "filename": filename,
        "extension": extension,
        "parent_dir": parent_dir,
        "size_bytes": size_bytes,
        "content_hash": content_hash,
        "hash_algo": "sha256",
        "mime_type": mime_type,
        "modified_at": modified_at,
        "is_deleted": False,
    }


def should_ignore_path(path: Path, ignore_patterns: list[str]) -> bool:
    """
    Check if a path should be ignored based on patterns.

    Args:
        path: Path to check
        ignore_patterns: List of patterns to match against

    Returns:
        True if path should be ignored
    """
    path_str = str(path)
    name = path.name

    for pattern in ignore_patterns:
        # Check if pattern matches filename or is in path
        if pattern.startswith("*"):
            # Wildcard pattern (e.g., "*.pyc")
            suffix = pattern[1:]
            if name.endswith(suffix):
                return True
        else:
            # Exact name or directory match
            if name == pattern or f"/{pattern}/" in path_str or path_str.endswith(f"/{pattern}"):
                return True
            # Windows path separators
            if f"\\{pattern}\\" in path_str or path_str.endswith(f"\\{pattern}"):
                return True

    return False


def scan_workspace(
    workspace_root: Path,
    ignore_patterns: list[str],
    max_size_mb: int = 100,
) -> list[dict]:
    """
    Scan workspace directory and extract metadata for all files.

    Args:
        workspace_root: The workspace root directory
        ignore_patterns: List of patterns to ignore
        max_size_mb: Maximum file size in MB to compute hash

    Returns:
        List of file metadata dictionaries
    """
    workspace_resolved = workspace_root.resolve()
    files = []

    if not workspace_resolved.exists():
        logger.warning(
            f"Workspace directory does not exist: {workspace_resolved}",
            extra={"extra_fields": {"workspace": str(workspace_resolved)}},
        )
        return files

    for root, dirs, filenames in os.walk(workspace_resolved):
        root_path = Path(root)

        # Filter out ignored directories (modify dirs in-place to prevent descent)
        dirs[:] = [
            d
            for d in dirs
            if not should_ignore_path(root_path / d, ignore_patterns)
            and not (root_path / d).is_symlink()
        ]

        for filename in filenames:
            file_path = root_path / filename

            # Skip ignored files
            if should_ignore_path(file_path, ignore_patterns):
                continue

            # Skip symlinks
            if file_path.is_symlink():
                logger.debug(
                    f"Skipping symlink: {file_path}",
                    extra={"extra_fields": {"path": str(file_path)}},
                )
                continue

            try:
                metadata = extract_file_metadata(
                    workspace_root, file_path, max_size_mb
                )
                files.append(metadata)
            except Exception as e:
                logger.warning(
                    f"Failed to extract metadata for {file_path}: {e}",
                    extra={
                        "extra_fields": {"path": str(file_path), "error": str(e)}
                    },
                )

    logger.info(
        f"Scanned workspace: {len(files)} files found",
        extra={
            "extra_fields": {
                "workspace": str(workspace_resolved),
                "file_count": len(files),
            }
        },
    )

    return files
