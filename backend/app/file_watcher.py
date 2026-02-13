"""
File Watcher Service for Agent B (B1.2).

Provides real-time file system monitoring for the workspace directory:
- Initial scan on startup (indexes all existing files)
- Watch for file changes via watchfiles
- Update FileIndex table on create/modify/delete
- Broadcast file events via SSE to all connected sessions
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from watchfiles import awatch, Change

from .config import get_settings
from .database import Database
from .file_service import (
    PathSecurityError,
    extract_file_metadata,
    get_relative_path,
    should_ignore_path,
    scan_workspace,
    validate_path_safety,
)
from .logging_config import get_logger
from .models import FileIndex

logger = get_logger("file_watcher")


class FileWatcher:
    """
    Watches workspace directory for file changes and maintains the FileIndex.

    Responsibilities:
    - Initial scan on startup (populate FileIndex with all files)
    - Watch for changes via watchfiles.awatch()
    - Update FileIndex on create/modify/delete
    - Broadcast SSE events for real-time UI updates
    """

    def __init__(
        self,
        workspace_dir: str,
        database: Database,
        broadcast_callback: Optional[callable] = None,
    ):
        """
        Initialize the file watcher.

        Args:
            workspace_dir: Path to the workspace directory to watch
            database: Database instance for FileIndex operations
            broadcast_callback: Optional callback(event_type, data) for SSE broadcasting
        """
        self.workspace_path = Path(workspace_dir).resolve()
        self.database = database
        self.broadcast_callback = broadcast_callback

        settings = get_settings()
        self.ignore_patterns = settings.file_watcher_ignore_patterns
        self.max_file_size_mb = settings.max_file_size_mb
        self.debounce_ms = settings.file_watcher_debounce_ms

        self._watch_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            f"FileWatcher initialized for: {self.workspace_path}",
            extra={
                "extra_fields": {
                    "workspace": str(self.workspace_path),
                    "ignore_patterns": self.ignore_patterns,
                }
            },
        )

    async def start(self) -> None:
        """
        Start the file watcher.

        1. Ensure workspace directory exists
        2. Perform initial scan to populate FileIndex
        3. Start watching for changes
        """
        if self._running:
            logger.warning("FileWatcher already running")
            return

        # Ensure workspace exists
        if not self.workspace_path.exists():
            logger.warning(
                f"Workspace directory does not exist, creating: {self.workspace_path}"
            )
            self.workspace_path.mkdir(parents=True, exist_ok=True)

        self._running = True

        # Initial scan
        await self._initial_scan()

        # Start watch task
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info("FileWatcher started")

    async def stop(self) -> None:
        """Stop the file watcher gracefully."""
        if not self._running:
            return

        self._running = False

        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

        logger.info("FileWatcher stopped")

    async def _initial_scan(self) -> None:
        """
        Perform initial workspace scan and populate FileIndex.

        This runs in a threadpool to avoid blocking the event loop during
        hash computation for large numbers of files.
        """
        logger.info("Starting initial workspace scan...")

        # Run synchronous scan in threadpool
        loop = asyncio.get_event_loop()
        file_metadata_list = await loop.run_in_executor(
            None,
            scan_workspace,
            self.workspace_path,
            self.ignore_patterns,
            self.max_file_size_mb,
        )

        if not file_metadata_list:
            logger.info("No files found in workspace")
            return

        # Batch insert/update to database
        async with self.database.session() as db_session:
            await self._batch_upsert_files(db_session, file_metadata_list)

        logger.info(
            f"Initial scan complete: {len(file_metadata_list)} files indexed",
            extra={"extra_fields": {"file_count": len(file_metadata_list)}},
        )

    async def _batch_upsert_files(
        self,
        db_session: AsyncSession,
        file_metadata_list: list[dict],
    ) -> None:
        """
        Batch upsert files to FileIndex.

        Uses INSERT ... ON CONFLICT for efficiency.
        """
        for metadata in file_metadata_list:
            # Check if file exists
            result = await db_session.execute(
                select(FileIndex).where(FileIndex.path == metadata["path"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.filename = metadata["filename"]
                existing.extension = metadata["extension"]
                existing.parent_dir = metadata["parent_dir"]
                existing.size_bytes = metadata["size_bytes"]
                existing.content_hash = metadata["content_hash"]
                existing.mime_type = metadata["mime_type"]
                existing.modified_at = metadata["modified_at"]
                existing.indexed_at = datetime.now(timezone.utc)
                existing.is_deleted = False  # Restore if was soft-deleted
            else:
                # Insert new record
                file_index = FileIndex(
                    id=metadata["id"],
                    path=metadata["path"],
                    filename=metadata["filename"],
                    extension=metadata["extension"],
                    parent_dir=metadata["parent_dir"],
                    size_bytes=metadata["size_bytes"],
                    content_hash=metadata["content_hash"],
                    hash_algo=metadata["hash_algo"],
                    mime_type=metadata["mime_type"],
                    modified_at=metadata["modified_at"],
                    is_deleted=False,
                )
                db_session.add(file_index)

        await db_session.commit()

    async def _watch_loop(self) -> None:
        """
        Main watch loop that listens for file system changes.

        Uses watchfiles.awatch() for efficient, cross-platform file watching.
        """
        try:
            logger.info(f"Starting file watch on: {self.workspace_path}")

            async for changes in awatch(
                self.workspace_path,
                debounce=self.debounce_ms,
                rust_timeout=5000,  # 5 second timeout for rust watcher
                yield_on_timeout=True,  # Allow heartbeat checks
            ):
                if not self._running:
                    break

                if not changes:
                    # Timeout with no changes (heartbeat)
                    continue

                await self._process_changes(changes)

        except asyncio.CancelledError:
            logger.info("File watch loop cancelled")
            raise
        except Exception as e:
            logger.error(
                f"File watcher error: {e}",
                exc_info=True,
                extra={"extra_fields": {"error": str(e)}},
            )
            # Don't re-raise - let the app continue in degraded mode

    async def _process_changes(self, changes: Set[tuple[Change, str]]) -> None:
        """
        Process a batch of file system changes.

        Args:
            changes: Set of (Change, path) tuples from watchfiles
        """
        for change_type, path_str in changes:
            try:
                path = Path(path_str)

                # Skip ignored paths
                if should_ignore_path(path, self.ignore_patterns):
                    continue

                # Skip directories (we only index files)
                if path.is_dir():
                    continue

                # Skip symlinks (security)
                if path.is_symlink():
                    logger.debug(f"Skipping symlink: {path}")
                    continue

                # Validate path safety
                try:
                    rel_path = get_relative_path(self.workspace_path, path)
                    validate_path_safety(self.workspace_path, rel_path)
                except PathSecurityError as e:
                    logger.warning(f"Path security violation: {e}")
                    continue
                except ValueError:
                    # Path not relative to workspace (shouldn't happen but be safe)
                    continue

                if change_type == Change.added:
                    await self._handle_file_created(path, rel_path)
                elif change_type == Change.modified:
                    await self._handle_file_modified(path, rel_path)
                elif change_type == Change.deleted:
                    await self._handle_file_deleted(rel_path)

            except Exception as e:
                logger.error(
                    f"Error processing change {change_type} for {path_str}: {e}",
                    exc_info=True,
                )

    async def _handle_file_created(self, path: Path, rel_path: str) -> None:
        """Handle file creation event."""
        logger.debug(f"File created: {rel_path}")

        # Extract metadata (runs hash in threadpool)
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None,
            extract_file_metadata,
            self.workspace_path,
            path,
            self.max_file_size_mb,
        )

        # Insert to database
        async with self.database.session() as db_session:
            # Check if already exists (might be a restore)
            result = await db_session.execute(
                select(FileIndex).where(FileIndex.path == rel_path)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing (un-delete if was soft-deleted)
                existing.filename = metadata["filename"]
                existing.extension = metadata["extension"]
                existing.parent_dir = metadata["parent_dir"]
                existing.size_bytes = metadata["size_bytes"]
                existing.content_hash = metadata["content_hash"]
                existing.mime_type = metadata["mime_type"]
                existing.modified_at = metadata["modified_at"]
                existing.indexed_at = datetime.now(timezone.utc)
                existing.is_deleted = False
                file_id = existing.id
            else:
                file_index = FileIndex(
                    id=metadata["id"],
                    path=rel_path,
                    filename=metadata["filename"],
                    extension=metadata["extension"],
                    parent_dir=metadata["parent_dir"],
                    size_bytes=metadata["size_bytes"],
                    content_hash=metadata["content_hash"],
                    hash_algo=metadata["hash_algo"],
                    mime_type=metadata["mime_type"],
                    modified_at=metadata["modified_at"],
                    is_deleted=False,
                )
                db_session.add(file_index)
                file_id = file_index.id

            await db_session.commit()

        # Broadcast SSE event
        await self._broadcast_file_event("file_created", {
            "file_id": file_id,
            "path": rel_path,
            "filename": metadata["filename"],
            "extension": metadata["extension"],
            "size_bytes": metadata["size_bytes"],
            "modified_at": metadata["modified_at"].isoformat(),
        })

    async def _handle_file_modified(self, path: Path, rel_path: str) -> None:
        """Handle file modification event."""
        logger.debug(f"File modified: {rel_path}")

        # Extract metadata
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None,
            extract_file_metadata,
            self.workspace_path,
            path,
            self.max_file_size_mb,
        )

        # Update database
        async with self.database.session() as db_session:
            result = await db_session.execute(
                select(FileIndex).where(FileIndex.path == rel_path)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.filename = metadata["filename"]
                existing.extension = metadata["extension"]
                existing.parent_dir = metadata["parent_dir"]
                existing.size_bytes = metadata["size_bytes"]
                existing.content_hash = metadata["content_hash"]
                existing.mime_type = metadata["mime_type"]
                existing.modified_at = metadata["modified_at"]
                existing.indexed_at = datetime.now(timezone.utc)
                existing.is_deleted = False
                file_id = existing.id
                await db_session.commit()
            else:
                # File was modified but not in index - treat as create
                await self._handle_file_created(path, rel_path)
                return

        # Broadcast SSE event
        await self._broadcast_file_event("file_modified", {
            "file_id": file_id,
            "path": rel_path,
            "filename": metadata["filename"],
            "extension": metadata["extension"],
            "size_bytes": metadata["size_bytes"],
            "content_hash": metadata["content_hash"],
            "modified_at": metadata["modified_at"].isoformat(),
        })

    async def _handle_file_deleted(self, rel_path: str) -> None:
        """Handle file deletion event (soft delete)."""
        logger.debug(f"File deleted: {rel_path}")

        # Soft delete in database
        async with self.database.session() as db_session:
            result = await db_session.execute(
                select(FileIndex).where(FileIndex.path == rel_path)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.is_deleted = True
                existing.indexed_at = datetime.now(timezone.utc)
                file_id = existing.id
                await db_session.commit()
            else:
                # Not in index - nothing to do
                return

        # Broadcast SSE event
        await self._broadcast_file_event("file_deleted", {
            "file_id": file_id,
            "path": rel_path,
        })

    async def _broadcast_file_event(self, event_type: str, data: dict) -> None:
        """
        Broadcast a file event to all connected SSE clients.

        Args:
            event_type: One of 'file_created', 'file_modified', 'file_deleted'
            data: Event data dictionary
        """
        if self.broadcast_callback:
            try:
                await self.broadcast_callback(event_type, data)
            except Exception as e:
                logger.error(f"Failed to broadcast file event: {e}", exc_info=True)

        logger.debug(
            f"File event: {event_type}",
            extra={"extra_fields": {"event_type": event_type, "data": data}},
        )


# =============================================================================
# SSE Broadcasting Integration
# =============================================================================

# Reference to session event queues (set during app startup)
_session_event_queues = None


def set_session_event_queues(queues: dict) -> None:
    """
    Set the reference to session event queues for SSE broadcasting.

    Called during app startup to connect file watcher to SSE infrastructure.

    Args:
        queues: The _session_event_queues dict from message_routes
    """
    global _session_event_queues
    _session_event_queues = queues
    logger.debug("Session event queues registered for file broadcasting")


async def broadcast_file_event_to_all_sessions(event_type: str, data: dict) -> None:
    """
    Broadcast a file event to all active SSE session queues.

    This is the callback passed to FileWatcher for SSE integration.

    Args:
        event_type: The SSE event type (file_created, file_modified, file_deleted)
        data: Event data dictionary
    """
    if _session_event_queues is None:
        logger.warning("Session event queues not initialized, skipping broadcast")
        return

    # Generate unique event ID
    event_id = str(uuid4())

    # Broadcast to all active session queues
    for session_id, queue in list(_session_event_queues.items()):
        try:
            await queue.put((event_type, data, event_id))
        except Exception as e:
            logger.warning(f"Failed to broadcast to session {session_id}: {e}")
