"""Unit tests for server-side attachment persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.attachments import cleanup_session_uploads, persist_attachments, resolve_storage_root


class _FakeUpload:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload
        self.seek_calls = 0

    def read(self) -> bytes:
        return self._payload

    def seek(self, offset: int, whence: int = 0) -> int:
        del offset, whence
        self.seek_calls += 1
        return 0


class AttachmentTests(unittest.TestCase):
    """Behavior tests for attachment persistence and limits."""

    def test_persists_supported_attachment_to_session_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upload = _FakeUpload("memo.md", b"hello world")
            result = persist_attachments(
                [upload],
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
                allowed_extensions=("txt", "md"),
                max_file_bytes=1024,
            )

            self.assertEqual(len(result.attachments), 1)
            self.assertEqual(result.attachments[0].filename, "memo.md")
            self.assertEqual(result.attachments[0].size_bytes, 11)
            self.assertTrue(result.attachments[0].relative_path.startswith("uploads/session-1/"))
            saved_path = root / result.attachments[0].relative_path
            self.assertEqual(saved_path.read_bytes(), b"hello world")
            self.assertEqual(result.warnings, [])
            self.assertEqual(upload.seek_calls, 1)

    def test_skips_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = persist_attachments(
                [_FakeUpload("image.png", b"binary")],
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
                allowed_extensions=("txt", "md"),
                max_file_bytes=1024,
            )

            self.assertEqual(result.attachments, [])
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("unsupported extension", result.warnings[0])

    def test_skips_attachment_when_size_exceeds_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = persist_attachments(
                [_FakeUpload("large.txt", b"x" * 10)],
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
                allowed_extensions=("txt",),
                max_file_bytes=5,
            )

            self.assertEqual(result.attachments, [])
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("file size exceeds", result.warnings[0])

    def test_duplicate_filename_gets_unique_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = persist_attachments(
                [
                    _FakeUpload("note.txt", b"one"),
                    _FakeUpload("note.txt", b"two"),
                ],
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
                allowed_extensions=("txt",),
                max_file_bytes=1024,
            )

            self.assertEqual(len(result.attachments), 2)
            rel_paths = [attachment.relative_path for attachment in result.attachments]
            self.assertNotEqual(rel_paths[0], rel_paths[1])
            self.assertEqual((root / rel_paths[0]).read_bytes(), b"one")
            self.assertEqual((root / rel_paths[1]).read_bytes(), b"two")

    def test_cleanup_session_uploads_removes_session_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = persist_attachments(
                [_FakeUpload("memo.md", b"hello world")],
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
                allowed_extensions=("md",),
                max_file_bytes=1024,
            )
            saved_path = root / result.attachments[0].relative_path
            self.assertTrue(saved_path.exists())

            cleanup_session_uploads(
                project_root=root,
                storage_dir="uploads",
                session_id="session-1",
            )

            self.assertFalse(saved_path.parent.exists())

    def test_resolve_storage_root_rejects_directory_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                resolve_storage_root(project_root=root, storage_dir="../outside")
