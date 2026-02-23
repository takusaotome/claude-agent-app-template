"""Unit tests for knowledge markdown discovery and search."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.knowledge import (
    KnowledgeMatch,
    build_knowledge_pattern,
    build_knowledge_preamble,
    list_knowledge_markdown_files,
    resolve_knowledge_dir,
    search_knowledge_markdown,
)


class KnowledgeTests(unittest.TestCase):
    """Validate directory safety, file listing, and search behavior."""

    def test_resolve_knowledge_dir_rejects_paths_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                resolve_knowledge_dir(root, "../outside")

    def test_list_markdown_files_returns_project_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "a.md").write_text("A", encoding="utf-8")
            (knowledge / "b.txt").write_text("B", encoding="utf-8")
            (knowledge / "nested").mkdir()
            (knowledge / "nested" / "c.md").write_text("C", encoding="utf-8")

            files = list_knowledge_markdown_files(knowledge, root)

        self.assertEqual(files, ["knowledge/a.md", "knowledge/nested/c.md"])

    def test_build_pattern_escapes_special_characters(self) -> None:
        pattern = build_knowledge_pattern("auth? token+")
        self.assertIn(r"\bauth\b", pattern)
        self.assertIn(r"token\+", pattern)

    def test_build_pattern_skips_english_stopwords(self) -> None:
        pattern = build_knowledge_pattern("What is the recommended auth mode?")
        self.assertIn(r"\brecommended\b", pattern)
        self.assertIn(r"\bauth\b", pattern)
        self.assertIn(r"\bmode\b", pattern)
        self.assertNotIn("What", pattern)
        self.assertNotIn("the", pattern)

    def test_build_pattern_removes_duplicate_terms_case_insensitive(self) -> None:
        pattern = build_knowledge_pattern("Auth auth AUTH")
        self.assertEqual(pattern, r"\bAuth\b")

    def test_build_pattern_keeps_single_cjk_token(self) -> None:
        pattern = build_knowledge_pattern("認 認証")
        self.assertIn("認", pattern)

    def test_build_knowledge_preamble_format(self) -> None:
        preamble = build_knowledge_preamble(
            files=["knowledge/a.md", "knowledge/b.md"],
            matches=[KnowledgeMatch(path="knowledge/a.md", line=12, snippet="auth flow")],
        )

        self.assertIn("[KNOWLEDGE]", preamble)
        self.assertIn("- knowledge/a.md", preamble)
        self.assertIn("knowledge/a.md:12: auth flow", preamble)

    def test_search_returns_empty_for_blank_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "faq.md").write_text("content", encoding="utf-8")

            hits = search_knowledge_markdown(
                "   ",
                knowledge_dir=knowledge,
                project_root=root,
                max_hits=5,
            )

        self.assertEqual(hits, [])

    def test_search_parses_rg_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            target = knowledge / "guide.md"
            target.write_text("line1\nline2\nline3", encoding="utf-8")
            fake_stdout = f"{target}:3:line3\n"

            with patch(
                "agent.knowledge.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=fake_stdout,
                    stderr="",
                ),
            ):
                hits = search_knowledge_markdown(
                    "line3",
                    knowledge_dir=knowledge,
                    project_root=root,
                    max_hits=5,
                )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].path, "knowledge/guide.md")
        self.assertEqual(hits[0].line, 3)
        self.assertEqual(hits[0].snippet, "line3")

    def test_search_falls_back_when_rg_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "faq.md").write_text("How to authenticate\nUse API key", encoding="utf-8")

            with patch("agent.knowledge.subprocess.run", side_effect=FileNotFoundError):
                hits = search_knowledge_markdown(
                    "authenticate",
                    knowledge_dir=knowledge,
                    project_root=root,
                    max_hits=5,
                )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].path, "knowledge/faq.md")
