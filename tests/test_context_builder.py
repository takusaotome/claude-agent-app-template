"""Unit tests for prompt context builder."""

from __future__ import annotations

import unittest

from agent.attachments import StoredAttachment
from agent.context_builder import PromptContextBuilder


class PromptContextBuilderTests(unittest.TestCase):
    """Ensures context sections are composed with budget limits."""

    def test_build_with_user_message_only(self) -> None:
        builder = PromptContextBuilder("hello", max_chars=100)
        prompt = builder.build()
        self.assertIn("[USER_MESSAGE]", prompt)
        self.assertIn("hello", prompt)

    def test_build_includes_knowledge_and_attachments(self) -> None:
        builder = PromptContextBuilder("question", max_chars=500)
        builder.add_knowledge_preamble("[KNOWLEDGE]\n- knowledge/a.md")
        builder.add_attachments(
            [
                StoredAttachment(
                    filename="note.txt",
                    relative_path="uploads/session-1/note.txt",
                    size_bytes=12,
                )
            ]
        )

        prompt = builder.build()
        self.assertIn("[KNOWLEDGE]", prompt)
        self.assertIn("[ATTACHMENTS]", prompt)
        self.assertIn("uploads/session-1/note.txt", prompt)
        self.assertIn("Do not use WebSearch/WebFetch", prompt)
        self.assertIn("[USER_MESSAGE]", prompt)

    def test_build_truncates_context_when_budget_is_small(self) -> None:
        builder = PromptContextBuilder("question", max_chars=60)
        builder.add_knowledge_preamble("[KNOWLEDGE]\n" + ("x" * 200))
        prompt = builder.build()

        self.assertLessEqual(len(prompt), 60)
        self.assertIn("[USER_MESSAGE]", prompt)
