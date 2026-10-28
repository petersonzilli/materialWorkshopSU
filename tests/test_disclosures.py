# Copyright (c) 2026 Peterson Katagiri Zilli
# SPDX-License-Identifier: Apache-2.0
"""Check fictional-data disclosures and source attribution across the workflow."""

from pathlib import Path
import re
import tempfile
import unittest

import app


class DisclosureTests(unittest.TestCase):
    def test_every_case_file_has_one_fictional_content_notice(self):
        files = list(app.CASES_ROOT.rglob("*.md"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.relative_to(app.CASES_ROOT)):
                content = path.read_text(encoding="utf-8")
                self.assertEqual(content.count(app.DEMO_CASE_NOTICE), 1)
                self.assertIn("## Dados fictícios\n\n" + app.DEMO_CASE_NOTICE, content)

    def test_prompt_exports_match_runtime_disclosure(self):
        for path in (app.ROOT / "prompts").glob("*.md"):
            with self.subTest(prompt=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn(app.DEMO_ARTIFACT_NOTICE.rstrip(), text)
                self.assertIn("Never infer organizational endorsement", text)
                self.assertNotRegex(text, r"\bapproved\b")
        for path in (app.ROOT / "skills").glob("*/SKILL.md"):
            with self.subTest(skill=path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("user-provided direction", text)
                self.assertIn("Never infer organizational endorsement", text)
                self.assertNotRegex(text, r"\bapproved\b")

    def test_export_disclosure_is_idempotent_and_preserves_copy_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = {"company": "mobility-demo", "campaign": "campaign-002-reativacao"}
            campaign = root / "companies" / state["company"] / "campaigns" / state["campaign"]
            campaign.mkdir(parents=True)
            briefing = "# Briefing\n\n" + app.DEMO_CASE_NOTICE + "\n"
            (campaign / "briefing.md").write_text(briefing, encoding="utf-8")
            content = "# Copy\n\nTítulo: Consulte seu trajeto\nCorpo: Abra o app.\n"
            names = (
                "briefing-intake.md", "message-strategy.md", "master-copy.md",
                "master-copy-revision-01.md", "audience-review-01.md", "audience-diagnosis-01.md",
                "channel-copy.md", "channel-copy-revision-01.md", "rules-validation-01.md",
                "human-decision-request-01.md", "human-intervention-01.md", "human-review-package.md",
            )
            for name in names:
                (campaign / name).write_text(content, encoding="utf-8")
            app.label_demo_artifacts(root, state)
            app.label_demo_artifacts(root, state)
            self.assertEqual((campaign / "briefing.md").read_text(encoding="utf-8"), briefing)
            for name in names:
                with self.subTest(artifact=name):
                    self.assertEqual((campaign / name).read_text(encoding="utf-8"), app.DEMO_ARTIFACT_NOTICE + content)

    def test_product_conditions_and_editorial_limits_remain_defined(self):
        insurance = app.CASES_ROOT / "insurance-demo"
        disclosure = "A cobertura está sujeita à aprovação da análise de risco e aos termos da apólice."
        self.assertIn(disclosure, (insurance / "configurations/rules.md").read_text(encoding="utf-8"))
        self.assertIn(disclosure, (insurance / "campaigns/campaign-001-plano-protecao-vida/briefing.md").read_text(encoding="utf-8"))
        for company in ("insurance-demo", "mobility-demo"):
            rules = (app.CASES_ROOT / company / "configurations/rules.md").read_text(encoding="utf-8")
            self.assertRegex(rules, re.compile(r"título a 40 caracteres.*160 caracteres"))


if __name__ == "__main__":
    unittest.main()
