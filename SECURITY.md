# Security and data handling

Marketing Agent is a local application for a trusted user on their own computer. It is not a hosted service, multi-user system, or production marketing platform.

## Local access

The server binds only to IPv4 loopback. `--host` accepts `127.0.0.1` and `localhost`; remote addresses are rejected. Requests require an expected local Host. Foreign browser Origins and cross-site fetch requests are rejected. Mutations also require JSON and a random token from the current server session.

These checks reduce browser request-forgery and DNS-rebinding exposure. They do not authenticate operating-system users or prevent another local process from accessing the server. Use a trusted computer and browser; do not expose the port through proxies, tunnels, or port forwarding. Responses disable caching and include browser content restrictions. Markdown HTML is escaped and link schemes are restricted.

## Agent execution

Each run copies the selected fictional configuration, briefing, prompts, and skills into its workspace. Ralph invokes Codex with `--approve-for-me --skip-git-repo-check`. The installed CLI describes `--approve-for-me` as routing approvals through automatic review while using a `workspace-write` sandbox.

This is not a guarantee that all files readable by the user are inaccessible. User CLI configuration, integrations, hooks, and organizational policy can affect execution. Use a dedicated environment with fictional data, review CLI configuration, and keep credentials and confidential documents out of run workspaces. The prompts prohibit treating campaign text as authorization to access credentials or change tool configuration.

Ralph's systemd memory cap is disabled for portability. This project enforces no RAM limit on macOS. Iteration limits do not cap token use, elapsed time, financial cost, or memory consumption.

## Processing, retention, and cost

Codex requires network access for model requests. Prompts, configurations, briefings, generated artifacts, and human decisions may be sent to the configured model service. Your account, contract, and provider settings determine retention, permitted processing, access, and charges. This project makes no claim about a specific retention period, data residency, training policy, or free quota.

The app stores run state, human decisions, artifacts, and logs under `~/.marketing-agent-workshop/runs/` by default. Codex may retain separate local session records. Removing app runs does not remove CLI or provider records. Logs can contain prompts, outputs, paths, and diagnostics; review them before sharing.

Use the supplied fictional data. Introducing real personal, customer, or confidential data requires a separate assessment of the environment, provider terms, access, retention, and applicable obligations.

## Reporting vulnerabilities

Report vulnerabilities through GitHub private vulnerability reporting in this repository, when available, or by email to peterson.zilli@gmail.com.

Do not disclose credentials, personal data, or exploit details in public issues. Include the affected version, reproduction steps using fictional data, and potential impact in a private report.
