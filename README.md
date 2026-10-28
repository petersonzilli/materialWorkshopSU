# Marketing Agent

Marketing Agent is a local application by Peterson Katagiri Zilli for generating and reviewing campaign copy with iterative AI agents. It uses [Ralph](https://gitlab.com/gallego.cesar/ralph) to run Codex CLI, retain evidence between attempts, and request human decisions when the workflow cannot advance.

A browser interface shows company configurations, campaign briefings, progress, review findings, and generated Markdown artifacts. Two fictional companies illustrate the same workflow in different contexts: **VaiVem** for mobility and **Serena Vida** for insurance. The interface and sample campaign data use Brazilian Portuguese; source, prompts, skills, and documentation use English.

Results are drafts for human review. Synthetic personas provide qualitative perspectives, not customer research or predictions of campaign performance. Checking supplied rules is not legal or regulatory validation. The application does not send or publish campaigns.

## Requirements

- macOS or Linux with Bash and Python 3.9 or newer.
- Codex CLI installed, authenticated, and available as `codex` on PATH. See the [official setup instructions](https://developers.openai.com/codex/cli).
- A CLI version whose `codex exec --help` includes `--approve-for-me` and `--skip-git-repo-check`.
- Internet connectivity, access to the selected model, and sufficient account quota. Provider charges may apply.

The application requires no additional Python packages. Ralph is included in `vendor/ralph/`.

## Start

From the repository directory:

```bash
python3 app.py
```

Open <http://127.0.0.1:8765>. Stop the application with `Ctrl+C`. To choose a different port:

```bash
python3 app.py --port 8766
```

The server accepts local connections only. Reload the browser page after restarting it.

### Model

The default model is `gpt-6-luna`. Model availability depends on the authenticated account. To select another accessible model:

```bash
WORKSHOP_CODEX_MODEL="your-model-id" python3 app.py
```

### Data directory

Runs are stored in `~/.marketing-agent-workshop/runs/`. To use another location:

```bash
WORKSHOP_DATA_DIR="$HOME/marketing-agent-data" python3 app.py
```

Each run receives a copy of the selected configuration, briefing, prompts, and skills. Generated artifacts stay in that run's workspace. The source cases are not overwritten.

## Run a campaign

1. Select a company and campaign.
2. Review the company's general configuration, applicable product rules, and briefing.
3. Set independent attempt limits for the persona/master-copy and channel-rules loops. Each defaults to five, including the first attempt.
4. Select **Iniciar execução** and follow the stages, counters, evidence, and logs.
5. If a decision is requested, read the blocker and evidence, supply the missing information or direction, and resume. The affected loop starts a fresh count while retaining its history.
6. Review the package marked **Pronto para revisão humana** before considering any real-world use.

VaiVem includes weekday-pass, reactivation, first-trip, and small-business delivery campaigns. Serena Vida includes a life-protection campaign. All company, product, audience, price, and availability information belongs to the fictional examples.

## How it works

| Loop | Activities | Completion condition |
| --- | --- | --- |
| Personas and master copy | Briefing intake, message strategy, copy generation, and qualitative review from synthetic perspectives | No unresolved Critical or Material findings |
| Channel rules | Channel adaptation and checking all applicable supplied rules | Required rules pass and remaining review notes are recorded |

Ralph starts a fresh Codex session for each attempt. Prompts and skills define the task; saved artifacts and state provide context for subsequent attempts. Critical and Material findings require a supported correction or human decision. Minor findings are retained as notes.

A missing fact, conflicting rule, or exhausted attempt limit pauses the workflow with evidence and a specific request. Human input allows the affected cycle to resume. A change to the central message can return the campaign to persona review.

Artifacts and evidence are grouped by phase. Markdown is rendered with tables, browser timestamps use the viewer's time zone, and logs are retained per Ralph invocation. Case files carry a fictional-content notice. Exported artifacts also identify AI-generated content, the need for human review, and the limits of synthetic personas and rule checking. These disclosures remain outside campaign copy fields and their character counts.

## Execution and data handling

Codex runs with automatic approval review and the `workspace-write` sandbox. User configuration and organizational policy can affect behavior; this is not complete isolation from all user-readable files. Use a trusted environment and keep credentials, real customer data, and confidential information out of run workspaces.

Prompts, configurations, copy, and human decisions may be processed by the configured model provider. Account terms govern access, retention, and charges. Local logs and Codex session records can also retain inputs and outputs. Inspect them before sharing.

Iteration limits do not cap elapsed time, tokens, cost, or RAM. This application does not enforce a memory limit on macOS. Do not expose the local server through a tunnel, reverse proxy, or port forwarding. See [SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local checks and contribution guidelines, and the [Code of Conduct](CODE_OF_CONDUCT.md) for participation standards. Tests use simulated agent responses and do not require model access.

## License and disclaimer

Copyright (c) 2026 Peterson Katagiri Zilli. Licensed under [Apache-2.0](LICENSE). See [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md).

This open-source project is provided as is, with no commitment of production support. It does not constitute financial, legal, or professional advice. The license does not grant rights to third-party trademarks. Contact: peterson.zilli@gmail.com.
