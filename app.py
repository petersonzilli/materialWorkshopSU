#!/usr/bin/env python3
# Copyright (c) 2026 Peterson Katagiri Zilli
# SPDX-License-Identifier: Apache-2.0
"""Local marketing-copy workflow powered by Ralph and Codex."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
CASES_ROOT = ROOT / "cases"
DATA_ROOT = Path(os.environ.get("WORKSHOP_DATA_DIR", str(Path.home() / ".marketing-agent-workshop"))).expanduser()
RUNS_ROOT = DATA_ROOT / "runs"
STATIC_ROOT = ROOT / "static"
RALPH_SCRIPT = ROOT / "vendor" / "ralph" / "ralph-loop.sh"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{6}$")
MAX_LOOP_LIMIT = 25
SESSION_TOKEN = secrets.token_urlsafe(32)
DEMO_CASE_NOTICE = (
    "**Conteúdo fictício para demonstração.** Empresas, produtos, ofertas, públicos e condições "
    "descritos neste exemplo não representam uma operação comercial real."
)
DEMO_ARTIFACT_NOTICE = (
    f"> {DEMO_CASE_NOTICE}\n>\n"
    "> Conteúdo gerado por IA, sujeito a revisão humana. Personas sintéticas não substituem "
    "pesquisa com clientes. A checagem das regras fornecidas não constitui validação jurídica "
    "ou regulatória.\n\n"
)

RUN_LOCK = threading.RLock()
RUN_PROCESSES: dict[str, subprocess.Popen[str]] = {}
ACTIVE_RUNS: set[str] = set()
RUNNER_THREADS: dict[str, threading.Thread] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path, maximum: int = 16000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:maximum]
    except (OSError, UnicodeError):
        return ""


def read_tail(path: Path, maximum: int = 16000) -> str:
    try:
        with path.open("rb") as file:
            file.seek(0, os.SEEK_END)
            length = file.tell()
            file.seek(max(0, length - maximum))
            return file.read(maximum).decode("utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def label_demo_artifacts(run_dir: Path, state: dict[str, Any]) -> None:
    """Label completed generated files, keeping the disclaimer outside copy fields."""
    campaign_dir = run_dir / "companies" / state["company"] / "campaigns" / state["campaign"]
    for path in campaign_dir.glob("*.md"):
        if path.name == "briefing.md":
            continue
        content = path.read_text(encoding="utf-8")
        if not content.startswith(DEMO_ARTIFACT_NOTICE):
            path.write_text(DEMO_ARTIFACT_NOTICE + content, encoding="utf-8")


def archive_ralph_logs(run_dir: Path, loop_name: str) -> None:
    """Preserve separate invocations whose upstream log names can collide."""
    paths = list((run_dir / ".ralph" / "logs").glob("*.log"))
    if not paths:
        return
    invocation = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = run_dir / ".ralph" / "archive" / f"{invocation}-{loop_name}"
    archive.mkdir(parents=True, exist_ok=False)
    for path in paths:
        path.rename(archive / path.name)


def record_event(state: dict[str, Any], message: str, event_type: str = "info") -> None:
    events = state.setdefault("events", [])
    events.append({"at": now_iso(), "type": event_type, "message": message})
    state["events"] = events[-150:]
    state["updated_at"] = now_iso()


def case_path(company: str, campaign: str | None = None) -> Path:
    if not SLUG_RE.fullmatch(company):
        raise ValueError("Identificador de empresa inválido.")
    base = CASES_ROOT / company
    if not base.is_dir():
        raise FileNotFoundError("Empresa não encontrada.")
    if campaign is None:
        return base
    if not SLUG_RE.fullmatch(campaign):
        raise ValueError("Identificador de campanha inválido.")
    campaign_path = base / "campaigns" / campaign
    if not campaign_path.is_dir():
        raise FileNotFoundError("Campanha não encontrada.")
    return campaign_path


def case_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    if not CASES_ROOT.is_dir():
        return catalog
    for company_dir in sorted(path for path in CASES_ROOT.iterdir() if path.is_dir()):
        configuration_dir = company_dir / "configurations"
        configurations = [
            {"name": path.name, "content": read_text(path, 10000)}
            for path in sorted(configuration_dir.glob("*.md"))
        ]
        campaigns: list[dict[str, Any]] = []
        campaigns_root = company_dir / "campaigns"
        if campaigns_root.is_dir():
            for campaign_dir in sorted(path for path in campaigns_root.iterdir() if path.is_dir()):
                briefing = read_text(campaign_dir / "briefing.md", 10000)
                artifact_names = sorted(path.name for path in campaign_dir.glob("*.md"))
                campaigns.append(
                    {
                        "id": campaign_dir.name,
                        "briefing": briefing,
                        "artifacts": artifact_names,
                    }
                )
        company_md = next((item["content"] for item in configurations if item["name"] == "company.md"), "")
        display_name = next((line.lstrip("# ").strip() for line in company_md.splitlines() if line.startswith("# ")), company_dir.name)
        catalog.append(
            {
                "id": company_dir.name,
                "name": display_name,
                "configurations": configurations,
                "campaigns": campaigns,
            }
        )
    return catalog


def valid_run_dir(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("Identificador da execução inválido.")
    path = RUNS_ROOT / run_id
    if not path.is_dir():
        raise FileNotFoundError("Execução não encontrada.")
    return path


def run_state_path(run_dir: Path) -> Path:
    return run_dir / "run-state.json"


def current_run_state(run_id: str) -> dict[str, Any]:
    state = read_json(run_state_path(valid_run_dir(run_id)))
    if state is None:
        raise FileNotFoundError("Não foi possível ler o estado da execução.")
    if state.get("human_request"):
        state["human_request"] = normalize_human_request(state["human_request"])
    return state


def list_runs() -> list[dict[str, Any]]:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    found: list[dict[str, Any]] = []
    with RUN_LOCK:
        active_ids = set(ACTIVE_RUNS)
    for run_dir in sorted((path for path in RUNS_ROOT.iterdir() if path.is_dir()), reverse=True):
        state = read_json(run_state_path(run_dir))
        if state:
            if state.get("human_request"):
                state["human_request"] = normalize_human_request(state["human_request"])
            if state.get("status") == "running" and run_dir.name not in active_ids:
                state["status"] = "error"
                record_event(state, "A execução foi interrompida antes do servidor atual iniciar. Consulte os artefatos antes de retomar.", "error")
                write_json(run_state_path(run_dir), state)
            found.append(state)
    return found[:40]


def make_ralph_env(run_dir: Path) -> None:
    model = os.environ.get("WORKSHOP_CODEX_MODEL", "gpt-6-luna")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
        raise ValueError("WORKSHOP_CODEX_MODEL deve conter um identificador de modelo válido.")
    env_path = run_dir / ".ralph" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    # Override Ralph's permissive default Codex flags with the user's workspace sandbox.
    env_path.write_text(
        "\n".join(
            [
                "RALPH_TOOL=codex",
                "RALPH_MODEL_CAPABILITY=med",
                f"RALPH_CODEX_MODEL_MED={model}",
                "RALPH_THINKING=false",
                "RALPH_SWITCH_ON_EXHAUSTION=false",
                "RALPH_MEMORY_MAX=",
                'RALPH_CODEX_FLAGS="--approve-for-me --skip-git-repo-check"',
                "RALPH_LOOP_MAX_LOGS=50",
                "",
            ]
        ),
        encoding="utf-8",
    )


def create_run(payload: dict[str, Any]) -> dict[str, Any]:
    company = str(payload.get("company", ""))
    campaign = str(payload.get("campaign", ""))
    source_campaign = case_path(company, campaign)
    source_company = case_path(company)
    source_briefing = source_campaign / "briefing.md"
    if not source_briefing.is_file():
        raise ValueError("A campanha selecionada não contém briefing.md.")

    limits: dict[str, int] = {}
    for loop_name in ("audience", "rules"):
        raw_limit = payload.get(f"{loop_name}_max", 5)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"O limite do ciclo de {loop_name} deve ser um número inteiro.") from exc
        if limit < 1 or limit > MAX_LOOP_LIMIT:
            raise ValueError(f"O limite do ciclo de {loop_name} deve estar entre 1 e {MAX_LOOP_LIMIT}.")
        limits[loop_name] = limit

    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(3).hex()
    run_dir = RUNS_ROOT / run_id
    config_destination = run_dir / "companies" / company / "configurations"
    campaign_destination = run_dir / "companies" / company / "campaigns" / campaign
    config_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_company / "configurations", config_destination)
    campaign_destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_briefing, campaign_destination / "briefing.md")
    (run_dir / "prompts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "prompts" / "audience-loop.md", run_dir / "prompts" / "audience-loop.md")
    shutil.copy2(ROOT / "prompts" / "rules-loop.md", run_dir / "prompts" / "rules-loop.md")
    shutil.copytree(ROOT / "skills", run_dir / "skills")
    make_ralph_env(run_dir)

    campaign_relative = f"companies/{company}/campaigns/{campaign}"
    configuration_relative = f"companies/{company}/configurations"
    state: dict[str, Any] = {
        "id": run_id,
        "company": company,
        "company_name": next((item["name"] for item in case_catalog() if item["id"] == company), company),
        "campaign": campaign,
        "status": "ready",
        "stage": "Briefing intake",
        "active_loop": "audience",
        "log_timezone": "UTC",
        "limits": limits,
        "iterations": {"audience": 0, "rules": 0},
        "human_request": None,
        "human_responses": [],
        "events": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "result": None,
    }
    record_event(state, "Run criado a partir do briefing e das configurações selecionadas.")
    write_json(run_state_path(run_dir), state)
    write_json(
        run_dir / "agent-state.json",
        {
            "schema_version": 1,
            "company": company,
            "company_name": state["company_name"],
            "campaign": campaign,
            "configuration_path": configuration_relative,
            "campaign_path": campaign_relative,
            "status": "ready",
            "stage": "Briefing intake",
            "active_loop": "audience",
            "log_timezone": "UTC",
            "limits": limits,
            "iterations": {"audience": 0, "rules": 0},
            "human_request": None,
            "human_responses": [],
            "findings": [],
            "attempt_history": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        },
    )
    return state


def merge_agent_state(run_id: str) -> dict[str, Any]:
    run_dir = valid_run_dir(run_id)
    state = read_json(run_state_path(run_dir)) or {}
    agent_state = read_json(run_dir / "agent-state.json") or {}
    for key in ("stage", "active_loop", "iterations", "human_request", "result", "decision"):
        if key in agent_state:
            value = agent_state[key]
            state[key] = normalize_human_request(value) if key == "human_request" and value else value
    state["agent_status"] = agent_state.get("status")
    state["agent_updated_at"] = agent_state.get("updated_at")
    return state


def mark_status(run_id: str, status: str, message: str, event_type: str = "info") -> dict[str, Any]:
    run_dir = valid_run_dir(run_id)
    state = read_json(run_state_path(run_dir)) or {}
    state["status"] = status
    record_event(state, message, event_type)
    write_json(run_state_path(run_dir), state)
    return state


def stop_signal(run_dir: Path) -> Path:
    return run_dir / "stop.md"


def evidence_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def normalize_evidence(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    entries = value if isinstance(value, list) else [value]
    summary_keys = ("summary", "finding", "outcome", "claim", "title", "message")
    source_keys = ("source", "artifact", "file", "reference", "path")
    detail_keys = ("detail", "evidence", "description", "quote", "reason")
    recognized_keys = set(summary_keys + source_keys + detail_keys)
    normalized: list[dict[str, str]] = []

    for entry in entries:
        if isinstance(entry, dict):
            summary = next((evidence_text(entry.get(key)) for key in summary_keys if evidence_text(entry.get(key))), "")
            source = next((evidence_text(entry.get(key)) for key in source_keys if evidence_text(entry.get(key))), "")
            detail = next((evidence_text(entry.get(key)) for key in detail_keys if evidence_text(entry.get(key))), "")
            additional = {key: item for key, item in entry.items() if key not in recognized_keys}
            if additional:
                extra_text = "Informações adicionais:\n" + json.dumps(additional, ensure_ascii=False, indent=2)
                detail = f"{detail}\n\n{extra_text}".strip()
            if not any((summary, source, detail)):
                summary = json.dumps(entry, ensure_ascii=False, indent=2)
            elif not summary:
                summary = detail or source
        else:
            summary = evidence_text(entry)
            source = ""
            detail = ""

        if summary or source or detail:
            normalized.append({"summary": summary, "source": source, "detail": detail})
    return normalized


def normalize_human_request(request: Any) -> dict[str, Any]:
    normalized = dict(request) if isinstance(request, dict) else {}
    normalized["evidence"] = normalize_evidence(normalized.get("evidence"))
    return normalized


def markdown_evidence_value(value: str) -> str:
    escaped = re.sub(r"([\\`*_{}\[\]()#+.!|>])", r"\\\1", value.strip())
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def format_evidence_markdown(value: Any) -> str:
    evidence = normalize_evidence(value)
    if not evidence:
        return "Consulte os artefatos e o log do Ralph desta execução."

    items: list[str] = []
    for item in evidence:
        lines = [f"- **Resumo:** {markdown_evidence_value(item['summary'])}"]
        if item["source"]:
            source = item["source"].replace("`", "\\`").replace("\n", " ")
            lines.append(f"  - **Origem:** `{source}`")
        if item["detail"]:
            lines.append(f"  - **Detalhe:** {markdown_evidence_value(item['detail'])}")
        items.append("\n".join(lines))
    return "\n".join(items)


def write_human_request_report(
    run_dir: Path,
    state: dict[str, Any],
    request: dict[str, Any],
    loop_name: str,
    attempt_count: int,
    max_iterations: int,
) -> None:
    campaign_dir = run_dir / "companies" / state["company"] / "campaigns" / state["campaign"]
    request_number = len(state.get("human_responses", [])) + 1
    report_path = campaign_dir / f"human-decision-request-{request_number:02d}.md"
    if report_path.exists():
        return

    history = request.get("attempt_history", [])
    history_lines = []
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict):
                summary = item.get("summary") or item.get("finding") or item.get("outcome")
                if not summary:
                    summary = json.dumps(item, ensure_ascii=False)
            else:
                summary = str(item)
            history_lines.append(f"- {summary}")
    history_text = "\n".join(history_lines) or "- O agente não registrou um resumo estruturado das tentativas."
    artifacts = sorted(path.name for path in campaign_dir.glob("*.md") if path != report_path)
    artifact_text = "\n".join(f"- `{name}`" for name in artifacts) or "- Nenhum artefato de campanha foi registrado."
    report_path.write_text(
        DEMO_ARTIFACT_NOTICE + "# Solicitação de decisão humana\n\n"
        f"- Campanha: {state['company']} / {state['campaign']}\n"
        f"- Ciclo: {loop_name}\n"
        f"- Etapa: {state.get('stage', 'não informada')}\n"
        f"- Tentativas: {attempt_count} de {max_iterations}\n\n"
        f"## Impedimento\n\n{request.get('blocker', 'O agente não registrou o impedimento.')}\n\n"
        f"## Evidências para revisar\n\n{format_evidence_markdown(request.get('evidence'))}\n\n"
        f"## Histórico relevante\n\n{history_text}\n\n"
        f"## Artefatos para consultar\n\n{artifact_text}\n\n"
        f"## Ação humana necessária\n\n{request.get('action_required', 'Defina a correção ou informação necessária para retomar.')}\n",
        encoding="utf-8",
    )


def runner_thread(run_id: str) -> None:
    run_dir = valid_run_dir(run_id)
    try:
        while True:
            state = read_json(run_state_path(run_dir))
            if not state:
                raise RuntimeError("O arquivo de estado da execução foi perdido.")
            loop_name = state.get("active_loop", "audience")
            if loop_name not in ("audience", "rules"):
                raise RuntimeError(f"Ciclo ativo desconhecido: {loop_name}")
            prompt_path = f"prompts/{loop_name}-loop.md"
            max_iterations = int(state["limits"][loop_name])
            signal = stop_signal(run_dir)
            if signal.exists():
                signal.unlink()

            agent_state = read_json(run_dir / "agent-state.json") or {}
            agent_state.update(
                {
                    "active_loop": loop_name,
                    "limits": state["limits"],
                    "status": "running",
                    "stage": state.get("stage", agent_state.get("stage")),
                    "updated_at": now_iso(),
                }
            )
            write_json(run_dir / "agent-state.json", agent_state)

            mark_status(run_id, "running", f"Iniciando o ciclo de {'audiência' if loop_name == 'audience' else 'regras'}.")
            output_path = run_dir / ".ralph" / "driver.log"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("a", encoding="utf-8") as output_file:
                output_file.write(f"\n\n=== {now_iso()} · {loop_name} · max {max_iterations} ===\n")
                process_environment = os.environ.copy()
                process_environment["TZ"] = "UTC"
                process = subprocess.Popen(
                    ["bash", str(RALPH_SCRIPT), str(max_iterations), prompt_path],
                    cwd=run_dir,
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=process_environment,
                    start_new_session=True,
                )
                with RUN_LOCK:
                    RUN_PROCESSES[run_id] = process
                return_code = process.wait()
                with RUN_LOCK:
                    RUN_PROCESSES.pop(run_id, None)

            archive_ralph_logs(run_dir, loop_name)
            state = read_json(run_state_path(run_dir)) or {}
            label_demo_artifacts(run_dir, state)
            agent_state = read_json(run_dir / "agent-state.json") or {}
            status = agent_state.get("status")
            if isinstance(agent_state.get("iterations"), dict):
                state["iterations"] = agent_state["iterations"]
            if agent_state.get("stage"):
                state["stage"] = agent_state["stage"]

            if status == "human_required":
                request = normalize_human_request(agent_state.get("human_request") or {})
                state.update(
                    {
                        "status": "awaiting_human",
                        "human_request": request,
                        "stage": agent_state.get("stage", state.get("stage")),
                        "active_loop": loop_name,
                        "iterations": agent_state.get("iterations", state.get("iterations")),
                    }
                )
                record_event(state, "A execução pausou para uma decisão humana.", "human")
                write_json(run_state_path(run_dir), state)
                current_iterations = agent_state.get("iterations", state.get("iterations", {}))
                attempt_count = int(current_iterations.get(loop_name, 0)) if isinstance(current_iterations, dict) else 0
                write_human_request_report(run_dir, state, request, loop_name, attempt_count, max_iterations)
                break

            if loop_name == "audience" and status == "audience_ready":
                state.update(
                    {
                        "status": "running",
                        "active_loop": "rules",
                        "stage": "Adaptação de canal e validação de regras",
                        "iterations": agent_state.get("iterations", state.get("iterations")),
                        "human_request": None,
                    }
                )
                record_event(state, "Revisão qualitativa por personas concluída; avançando para adaptação de canal e regras.")
                write_json(run_state_path(run_dir), state)
                agent_state.update(
                    {
                        "active_loop": "rules",
                        "status": "running",
                        "stage": state["stage"],
                        "iterations": {**agent_state.get("iterations", {}), "rules": 0},
                        "human_request": None,
                        "updated_at": now_iso(),
                    }
                )
                state["iterations"]["rules"] = 0
                write_json(run_state_path(run_dir), state)
                write_json(run_dir / "agent-state.json", agent_state)
                continue

            if loop_name == "rules" and status == "rules_ready":
                state.update(
                    {
                        "status": "complete",
                        "stage": "Pronto para revisão humana",
                        "active_loop": "rules",
                        "iterations": agent_state.get("iterations", state.get("iterations")),
                        "human_request": None,
                        "result": "rules_ready",
                    }
                )
                record_event(state, "A checagem das regras fictícias terminou; o copy está pronto para revisão humana.", "success")
                write_json(run_state_path(run_dir), state)
                break

            if status == "audience_recheck":
                state.update(
                    {
                        "status": "running",
                        "active_loop": "audience",
                        "stage": "Revisão da audiência após alteração do master copy",
                        "iterations": agent_state.get("iterations", state.get("iterations")),
                    }
                )
                record_event(state, "Uma alteração material do copy retornou o fluxo à avaliação de audiência.")
                write_json(run_state_path(run_dir), state)
                agent_state.update(
                    {
                        "active_loop": "audience",
                        "status": "running",
                        "stage": state["stage"],
                        "updated_at": now_iso(),
                    }
                )
                write_json(run_dir / "agent-state.json", agent_state)
                continue

            current_iterations = agent_state.get("iterations", state.get("iterations", {}))
            attempt_count = int(current_iterations.get(loop_name, 0)) if isinstance(current_iterations, dict) else 0
            if attempt_count >= max_iterations and status not in ("audience_ready", "rules_ready"):
                request = normalize_human_request({
                    "title": "O ciclo atingiu o limite de tentativas",
                    "blocker": "O agente não registrou uma condição de avanço antes de esgotar o limite configurado.",
                    "evidence": "Revise os artefatos do ciclo e o log do Ralph nesta execução.",
                    "action_required": "Decida a correção ou informação necessária e registre-a para retomar o ciclo.",
                    "attempt_history": agent_state.get("attempt_history", []),
                })
                state.update(
                    {
                        "status": "awaiting_human",
                        "active_loop": loop_name,
                        "iterations": current_iterations,
                        "human_request": request,
                    }
                )
                record_event(state, "O limite foi atingido sem estado final; foi criada uma solicitação humana de segurança.", "human")
                write_json(run_state_path(run_dir), state)
                agent_state.update(
                    {
                        "status": "human_required",
                        "active_loop": loop_name,
                        "iterations": current_iterations,
                        "human_request": request,
                        "updated_at": now_iso(),
                    }
                )
                write_json(run_dir / "agent-state.json", agent_state)
                write_json(
                    run_dir / "human-decision-request.json",
                    {"created_at": now_iso(), "loop": loop_name, **request},
                )
                write_human_request_report(run_dir, state, request, loop_name, attempt_count, max_iterations)
                break

            if return_code != 0:
                mark_status(run_id, "error", f"Ralph encerrou com o código {return_code}. Consulte os logs desta execução.", "error")
            else:
                mark_status(run_id, "error", "O agente encerrou sem registrar uma decisão reconhecida. Consulte os artefatos e os logs.", "error")
            break
    except Exception as exc:  # Keep the local UI responsive on runner errors.
        try:
            mark_status(run_id, "error", f"Falha na execução: {exc}", "error")
        except Exception:
            pass
    finally:
        with RUN_LOCK:
            RUN_PROCESSES.pop(run_id, None)
            ACTIVE_RUNS.discard(run_id)
            if RUNNER_THREADS.get(run_id) is threading.current_thread():
                RUNNER_THREADS.pop(run_id, None)


def start_run(run_id: str) -> None:
    valid_run_dir(run_id)
    with RUN_LOCK:
        if ACTIVE_RUNS:
            raise RuntimeError("Outra execução está em andamento. Aguarde ela terminar antes de iniciar outro case.")
        ACTIVE_RUNS.add(run_id)
        thread = threading.Thread(target=runner_thread, args=(run_id,), daemon=True)
        RUNNER_THREADS[run_id] = thread
        try:
            thread.start()
        except RuntimeError:
            ACTIVE_RUNS.discard(run_id)
            RUNNER_THREADS.pop(run_id, None)
            raise


class WorkshopHandler(BaseHTTPRequestHandler):
    server_version = "MarketingAgent/0.1"

    def check_local_request(self, mutation: bool = False) -> bool:
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed_hosts.update({"127.0.0.1", "localhost"})
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        if len(hosts) != 1 or hosts[0].lower() not in allowed_hosts:
            self.send_json({"error": "Host local inválido."}, 403)
            return False
        allowed_origins = {f"http://{host}" for host in allowed_hosts}
        if (len(origins) > 1 or (origins and origins[0] not in allowed_origins)
                or self.headers.get("Sec-Fetch-Site") == "cross-site"):
            self.send_json({"error": "Requisição de outra origem bloqueada."}, 403)
            return False
        if mutation:
            token = self.headers.get("X-Workshop-Token", "")
            if not secrets.compare_digest(token.encode("utf-8"), SESSION_TOKEN.encode("utf-8")):
                self.send_json({"error": "Sessão inválida. Recarregue a página."}, 403)
                return False
            if self.headers.get_content_type() != "application/json":
                self.send_json({"error": "Use application/json."}, 415)
                return False
        return True

    def send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", (
            "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; font-src 'self'; img-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        ))

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 50000:
            raise ValueError("A solicitação é muito grande.")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(value, dict):
            raise ValueError("O conteúdo da solicitação precisa ser um objeto JSON.")
        return value

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self.check_local_request():
            return
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/":
                self.send_bytes((STATIC_ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/styles.css":
                self.send_bytes((STATIC_ROOT / "styles.css").read_bytes(), "text/css; charset=utf-8")
            elif path == "/app.js":
                self.send_bytes((STATIC_ROOT / "app.js").read_bytes(), "text/javascript; charset=utf-8")
            elif path == "/api/session":
                self.send_json({"token": SESSION_TOKEN})
            elif path == "/api/catalog":
                self.send_json({"companies": case_catalog()})
            elif path == "/api/runs":
                self.send_json({"runs": list_runs()})
            elif path.startswith("/api/runs/"):
                parts = path.split("/")
                if len(parts) == 4:
                    self.send_json({"run": merge_agent_state(parts[3])})
                elif len(parts) == 5 and parts[4] == "logs":
                    run_dir = valid_run_dir(parts[3])
                    log_text = read_tail(run_dir / ".ralph" / "driver.log", 40000)
                    ralph_logs = list((run_dir / ".ralph" / "logs").glob("*.log"))
                    ralph_logs.extend((run_dir / ".ralph" / "archive").glob("*/*.log"))
                    ralph_logs.sort(key=lambda log: log.stat().st_mtime_ns)
                    latest = read_tail(ralph_logs[-1], 16000) if ralph_logs else ""
                    self.send_json({"driver": log_text, "latest_iteration": latest})
                elif len(parts) == 5 and parts[4] == "artifacts":
                    run_dir = valid_run_dir(parts[3])
                    state = read_json(run_state_path(run_dir)) or {}
                    campaign_dir = run_dir / "companies" / state["company"] / "campaigns" / state["campaign"]
                    files = [
                        {"name": path.name, "content": read_text(path, 12000)}
                        for path in sorted(campaign_dir.glob("*.md"))
                    ]
                    self.send_json({"artifacts": files})
                else:
                    self.send_json({"error": "Rota não encontrada."}, 404)
            else:
                self.send_json({"error": "Rota não encontrada."}, 404)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except OSError:
            self.send_json({"error": "O arquivo solicitado não está disponível."}, 404)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self.check_local_request(mutation=True):
            return
        path = unquote(urlparse(self.path).path)
        try:
            payload = self.read_body()
            if path == "/api/runs":
                state = create_run(payload)
                self.send_json({"run": state}, 201)
                return

            parts = path.split("/")
            if len(parts) == 5 and parts[1:3] == ["api", "runs"] and parts[4] == "start":
                state = current_run_state(parts[3])
                if state.get("status") != "ready":
                    raise RuntimeError("Esta execução não pode ser iniciada no estado atual.")
                start_run(parts[3])
                self.send_json({"run": current_run_state(parts[3])}, 202)
                return

            if len(parts) == 5 and parts[1:3] == ["api", "runs"] and parts[4] == "human":
                run_id = parts[3]
                state = current_run_state(run_id)
                if state.get("status") != "awaiting_human":
                    raise RuntimeError("Esta execução não está aguardando uma decisão humana.")
                with RUN_LOCK:
                    if ACTIVE_RUNS:
                        raise RuntimeError("Outra execução está em andamento. Aguarde-a terminar antes de retomar este ciclo.")
                response = str(payload.get("response", "")).strip()
                if not response:
                    raise ValueError("Registre a decisão ou correção antes de retomar.")
                run_dir = valid_run_dir(run_id)
                request = state.get("human_request") or {}
                active_loop = state.get("active_loop", "audience")
                response_item = {"at": now_iso(), "loop": active_loop, "request": request, "response": response}
                state.setdefault("human_responses", []).append(response_item)
                campaign_dir = run_dir / "companies" / state["company"] / "campaigns" / state["campaign"]
                response_number = len(state["human_responses"])
                intervention_path = campaign_dir / f"human-intervention-{response_number:02d}.md"
                while intervention_path.exists():
                    response_number += 1
                    intervention_path = campaign_dir / f"human-intervention-{response_number:02d}.md"
                intervention_path.write_text(
                    DEMO_ARTIFACT_NOTICE + "# Intervenção humana\n\n"
                    f"- Ciclo: {active_loop}\n"
                    f"- Registrada em: {response_item['at']}\n\n"
                    "## Decisão ou orientação\n\n"
                    f"{response}\n",
                    encoding="utf-8",
                )
                state["human_request"] = None
                state["status"] = "running"
                state["iterations"][active_loop] = 0
                record_event(state, "Decisão humana registrada; a contagem do ciclo foi reiniciada.", "human")
                write_json(run_state_path(run_dir), state)
                agent_state = read_json(run_dir / "agent-state.json") or {}
                agent_state.setdefault("human_responses", []).append(response_item)
                agent_state.update(
                    {
                        "status": "running",
                        "active_loop": active_loop,
                        "iterations": state["iterations"],
                        "human_request": None,
                        "human_response": response_item,
                        "updated_at": now_iso(),
                    }
                )
                write_json(run_dir / "agent-state.json", agent_state)
                signal = stop_signal(run_dir)
                if signal.exists():
                    signal.unlink()
                request_file = run_dir / "human-decision-request.json"
                if request_file.exists():
                    request_file.unlink()
                previous_thread = RUNNER_THREADS.get(run_id)
                if previous_thread and previous_thread.is_alive():
                    previous_thread.join()
                start_run(run_id)
                self.send_json({"run": current_run_state(run_id)}, 202)
                return

            self.send_json({"error": "Rota não encontrada."}, 404)
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except RuntimeError as exc:
            self.send_json({"error": str(exc)}, 409)
        except OSError:
            self.send_json({"error": "Não foi possível acessar os arquivos da execução."}, 500)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Marketing Agent locally.")
    parser.add_argument("--host", choices=("127.0.0.1", "localhost"), default="127.0.0.1", help="Loopback only.")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765).")
    args = parser.parse_args()
    if not RALPH_SCRIPT.is_file():
        raise SystemExit("Ralph não foi encontrado. Consulte as instruções do README.")
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WorkshopHandler)
    server.daemon_threads = True
    print(f"Marketing Agent available at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the local server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Marketing Agent.")
    finally:
        with RUN_LOCK:
            active_processes = list(RUN_PROCESSES.items())
        for run_id, process in active_processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    process.kill()
            try:
                mark_status(run_id, "error", "O servidor foi encerrado durante a execução; consulte os artefatos antes de retomar.", "error")
            except (FileNotFoundError, ValueError):
                pass
        server.server_close()


if __name__ == "__main__":
    main()
