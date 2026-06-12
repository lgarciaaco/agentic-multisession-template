#!/usr/bin/env python3
"""Smoke tests for code-reviewer skill layout and synthesizer contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_code_review import synthesize_code_review_verdict  # noqa: E402

HUB_ROOT = Path(__file__).resolve().parent.parent
CODE_REVIEWER = HUB_ROOT / ".cursor/skills/code-reviewer"
FINDINGS_SCHEMA = CODE_REVIEWER / "references/findings-schema.md"
SKILL = CODE_REVIEWER / "SKILL.md"
SYNTHESIZER_RULES = CODE_REVIEWER / "rules/agents/synthesizer.md"


def _assert_code_reviewer_agent(
    test: unittest.TestCase,
    *,
    rel_paths: tuple[str, ...],
    schema_token: str,
    skill_phrases: tuple[str, ...] = (),
    rubric_path: str | None = None,
    rubric_sections: tuple[str, ...] = (),
) -> None:
    base = CODE_REVIEWER
    for rel in rel_paths:
        test.assertTrue((base / rel).is_file(), rel)
    schema = FINDINGS_SCHEMA.read_text()
    test.assertIn(schema_token, schema)
    if skill_phrases:
        skill = SKILL.read_text()
        for phrase in skill_phrases:
            test.assertIn(phrase, skill)
    if rubric_path and rubric_sections:
        rubric = (base / rubric_path).read_text()
        for section in rubric_sections:
            test.assertIn(section, rubric)


class CodeReviewerSkillSmokeTests(unittest.TestCase):
    def test_structure_reviewer_skill_present(self) -> None:
        _assert_code_reviewer_agent(
            self,
            rel_paths=(
                "agents/structure-reviewer.md",
                "rules/structure.md",
                "rules/agents/structure-reviewer.md",
            ),
            schema_token="structure",
            skill_phrases=("structure-reviewer", "triggers.structure"),
        )

    def test_infra_yaml_reviewer_skill_present(self) -> None:
        _assert_code_reviewer_agent(
            self,
            rel_paths=(
                "agents/infra-yaml-reviewer.md",
                "rules/infra-yaml.md",
                "rules/agents/infra-yaml-reviewer.md",
            ),
            schema_token="infra-yaml",
            skill_phrases=("infra-yaml-reviewer", "triggers.infra"),
            rubric_path="rules/infra-yaml.md",
            rubric_sections=("Ansible", "GitHub Actions", "BLOCKER allowed"),
        )

    def test_code_reviewer_mandates_task_specialists(self) -> None:
        text = SKILL.read_text()
        self.assertIn("Subagent isolation", text)
        self.assertIn("must **not**", text)
        self.assertIn("structure-reviewer", text)
        self.assertIn("infra-yaml-reviewer", text)

    def test_synthesizer_documents_infra_yaml_blocker_fail(self) -> None:
        text = SYNTHESIZER_RULES.read_text()
        self.assertIn("infra-yaml", text)
        self.assertIn("BLOCKER", text)
        self.assertIn("FAIL", text)

    def test_synthesize_fail_on_infra_yaml_blocker(self) -> None:
        docs = [
            {
                "agent": "infra-yaml",
                "findings": [
                    {
                        "severity": "BLOCKER",
                        "issue": "setup script overwrites live secrets on re-run",
                    }
                ],
            }
        ]
        self.assertEqual(synthesize_code_review_verdict(docs), "FAIL")

    def test_synthesize_fail_on_security_blocker(self) -> None:
        docs = [
            {
                "agent": "security",
                "findings": [{"severity": "BLOCKER", "issue": "hardcoded token"}],
            }
        ]
        self.assertEqual(synthesize_code_review_verdict(docs), "FAIL")


if __name__ == "__main__":
    unittest.main()
