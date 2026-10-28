# Copyright (c) 2026 Peterson Katagiri Zilli
# SPDX-License-Identifier: Apache-2.0
"""Exercise the HTTP boundary and real Ralph orchestration without model calls."""

import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import app


class LocalDemoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.run_patch = patch.object(app, "RUNS_ROOT", self.root / "runs")
        self.run_patch.start()
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.WorkshopHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        stub = self.bin_dir / "codex"
        shutil.copyfile(Path(__file__).parent / "fixtures" / "agent_stub.py", stub)
        stub.chmod(0o755)
        self.environment = patch.dict(os.environ, {
            "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
            "STUB_AUDIENCE_TARGET": "1", "STUB_RULES_TARGET": "1", "STUB_REQUEST_HUMAN": "0",
            "WORKSHOP_CODEX_MODEL": "gpt-6-luna",
        })
        self.environment.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.environment.stop()
        self.run_patch.stop()
        self.directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        request_headers = {"Host": self.host, **(headers or {})}
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        content = response.read()
        result = (response.status, content, dict(response.getheaders()))
        connection.close()
        return result

    def mutation_headers(self):
        status, content, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200)
        return {"Content-Type": "application/json", "Origin": f"http://{self.host}",
                "X-Workshop-Token": json.loads(content)["token"]}

    def create_run(self, company="mobility-demo", campaign="campaign-002-reativacao", **limits):
        return app.create_run({"company": company, "campaign": campaign, **limits})

    def test_foreign_hosts_origins_and_fetch_sites_are_blocked(self):
        for headers in ({"Host": "foreign.example"}, {"Origin": "https://foreign.example"},
                        {"Origin": "null"}, {"Origin": f"http://localhost:{self.port + 1}"},
                        {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("GET", "/api/session", headers=headers)[0], 403)

    def test_mutations_require_current_token_and_json(self):
        payload = json.dumps({"company": "mobility-demo", "campaign": "campaign-002-reativacao"})
        good = self.mutation_headers()
        for headers in ({"Content-Type": "application/json"},
                        {**good, "X-Workshop-Token": "wrong"},
                        {**good, "Origin": "https://foreign.example"}):
            self.assertEqual(self.request("POST", "/api/runs", payload, headers)[0], 403)
        self.assertEqual(self.request("POST", "/api/runs", payload, {**good, "Content-Type": "text/plain"})[0], 415)
        self.assertFalse(app.RUNS_ROOT.exists())
        status, content, headers = self.request("POST", "/api/runs", payload, good)
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(content)["run"]["limits"], {"audience": 5, "rules": 5})
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_browser_can_start_a_run_but_forged_start_cannot_launch_agent(self):
        run = self.create_run()
        path = f"/api/runs/{run['id']}/start"
        with patch.object(app, "start_run") as start:
            self.assertEqual(self.request("POST", path, "{}", {"Content-Type": "application/json"})[0], 403)
            start.assert_not_called()
            self.assertEqual(self.request("POST", path, "{}", self.mutation_headers())[0], 202)
            start.assert_called_once_with(run["id"])

    def test_all_five_campaigns_use_real_ralph_and_stop_without_extra_iteration(self):
        fixture_bytes = {path: path.read_bytes() for path in app.CASES_ROOT.rglob("*.md")}
        campaigns = [(company["id"], campaign["id"]) for company in app.case_catalog() for campaign in company["campaigns"]]
        self.assertEqual(len(campaigns), 5)
        for company, campaign in campaigns:
            with self.subTest(company=company, campaign=campaign):
                run = self.create_run(company, campaign)
                app.runner_thread(run["id"])
                final = app.current_run_state(run["id"])
                self.assertEqual(final["status"], "complete", final)
                self.assertEqual(final["iterations"], {"audience": 1, "rules": 1})
                directory = app.valid_run_dir(run["id"])
                self.assertEqual(len(list((directory / ".ralph/archive").glob("*/*.log"))), 2)
                status, logs, _ = self.request("GET", f"/api/runs/{run['id']}/logs")
                self.assertEqual(status, 200)
                self.assertIn("Offline CLI stub completed", json.loads(logs)["latest_iteration"])
                for artifact in (directory / "companies" / company / "campaigns" / campaign).glob("*.md"):
                    if artifact.name != "briefing.md":
                        self.assertTrue(artifact.read_text().startswith(app.DEMO_ARTIFACT_NOTICE))
        self.assertEqual(fixture_bytes, {path: path.read_bytes() for path in app.CASES_ROOT.rglob("*.md")})

    def test_supported_revision_uses_another_iteration(self):
        with patch.dict(os.environ, {"STUB_AUDIENCE_TARGET": "2"}):
            run = self.create_run(audience_max=3, rules_max=4)
            app.runner_thread(run["id"])
        final = app.current_run_state(run["id"])
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["iterations"], {"audience": 2, "rules": 1})

    def test_exhausted_limit_pauses_and_preserves_evidence(self):
        with patch.dict(os.environ, {"STUB_AUDIENCE_TARGET": "2"}):
            run = self.create_run(audience_max=1, rules_max=4)
            app.runner_thread(run["id"])
        final = app.current_run_state(run["id"])
        self.assertEqual(final["status"], "awaiting_human")
        self.assertEqual(final["iterations"], {"audience": 1, "rules": 0})
        directory = app.valid_run_dir(run["id"])
        report = next(directory.glob("companies/*/campaigns/*/human-decision-request-*.md"))
        self.assertTrue(report.read_text().startswith(app.DEMO_ARTIFACT_NOTICE))
        self.assertIn("cycle_attempt", (directory / "agent-state.json").read_text())

    def test_human_decision_resets_only_cycle_counter_and_retains_history(self):
        with patch.dict(os.environ, {"STUB_REQUEST_HUMAN": "1"}):
            run = self.create_run()
            app.runner_thread(run["id"])
            self.assertEqual(app.current_run_state(run["id"])["status"], "awaiting_human")
            with patch.object(app, "start_run", side_effect=app.runner_thread):
                status, _, _ = self.request("POST", f"/api/runs/{run['id']}/human",
                                           json.dumps({"response": "Condição fictícia definida para este teste."}),
                                           self.mutation_headers())
        self.assertEqual(status, 202)
        final = app.current_run_state(run["id"])
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["iterations"], {"audience": 1, "rules": 1})
        directory = app.valid_run_dir(run["id"])
        agent = app.read_json(directory / "agent-state.json")
        audience = [item for item in agent["attempt_history"] if item["loop"] == "audience"]
        self.assertEqual([item["attempt"] for item in audience], [1, 2])
        self.assertEqual([item["cycle_attempt"] for item in audience], [1, 1])
        self.assertIn("Condição fictícia", agent["human_responses"][0]["response"])
        report = next(directory.glob("companies/*/campaigns/*/human-intervention-*.md"))
        self.assertTrue(report.read_text().startswith(app.DEMO_ARTIFACT_NOTICE))

    def test_rules_limit_is_independent_from_audience_limit(self):
        with patch.dict(os.environ, {"STUB_RULES_TARGET": "2"}):
            run = self.create_run(audience_max=3, rules_max=1)
            app.runner_thread(run["id"])
        final = app.current_run_state(run["id"])
        self.assertEqual(final["status"], "awaiting_human")
        self.assertEqual(final["active_loop"], "rules")
        self.assertEqual(final["iterations"], {"audience": 1, "rules": 1})
        directory = app.valid_run_dir(run["id"])
        self.assertEqual(len(list((directory / ".ralph/archive").glob("*/*.log"))), 2)

    def test_invalid_model_cannot_inject_shell_configuration(self):
        with patch.dict(os.environ, {"WORKSHOP_CODEX_MODEL": "model\nINVALID=1"}):
            with self.assertRaises(ValueError):
                app.make_ralph_env(self.root / "invalid")

    def test_remote_bind_is_rejected_before_server_starts(self):
        result = subprocess.run([sys.executable, "-B", str(app.ROOT / "app.py"), "--host", "0.0.0.0"],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
