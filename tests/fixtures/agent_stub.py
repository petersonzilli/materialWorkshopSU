#!/usr/bin/env python3
# Copyright (c) 2026 Peterson Katagiri Zilli
# SPDX-License-Identifier: Apache-2.0
"""Offline test double for the CLI process; never calls a model service."""

import json
import os
import sys
from pathlib import Path

prompt = sys.stdin.read()
assert "Demonstration scope and task boundaries" in prompt
assert os.environ.get("TZ") == "UTC"
root = Path.cwd()
state_path = root / "agent-state.json"
state = json.loads(state_path.read_text())
loop = state["active_loop"]
state["iterations"][loop] += 1
count = state["iterations"][loop]
history = state.setdefault("attempt_history", [])
lifetime = sum(item.get("loop") == loop for item in history) + 1
history.append({"loop": loop, "attempt": lifetime, "cycle_attempt": count, "summary": "Offline test attempt"})
campaign = root / state["campaign_path"]
target = int(os.environ.get("STUB_AUDIENCE_TARGET" if loop == "audience" else "STUB_RULES_TARGET", "1"))
human = loop == "audience" and os.environ.get("STUB_REQUEST_HUMAN") == "1" and not state.get("human_responses")
if human:
    state["status"] = "human_required"
    state["human_request"] = {
        "title": "Decisão fictícia para teste",
        "blocker": "Falta uma condição fictícia.",
        "evidence": [{"summary": "Lacuna do teste", "source": "briefing.md", "detail": "Exemplo sintético."}],
        "action_required": "Registrar uma condição fictícia.",
        "attempt_history": ["Primeira tentativa sem condição."],
    }
elif count < target:
    state["status"] = "revision_required"
else:
    state["status"] = "audience_ready" if loop == "audience" else "rules_ready"
    names = ("master-copy.md", f"audience-review-{lifetime:02d}.md", f"audience-diagnosis-{lifetime:02d}.md") if loop == "audience" else ("channel-copy.md", f"rules-validation-{lifetime:02d}.md", "human-review-package.md")
    for name in names:
        path = campaign / name
        if not path.exists():
            path.write_text("# Artefato sintético de teste\n\nNão é uma campanha real.\n")
if state["status"] != "revision_required":
    (root / "stop.md").write_text("Offline test terminal outcome\n")
state_path.write_text(json.dumps(state, ensure_ascii=False))
if "-o" in sys.argv:
    Path(sys.argv[sys.argv.index("-o") + 1]).write_text("Offline agent response\n")
print("Offline CLI stub completed")
