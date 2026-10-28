# Contributing

Contributions follow this guide and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Issues and pull requests

For a bug report, include reproduction steps, expected behavior, operating system, Python and Codex CLI versions, and a minimal example using fictional data. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

Discuss substantial changes in an issue before implementing them. Submit focused pull requests with relevant tests and documentation. The maintainer manages review and releases.

Do not include credentials, internal addresses, real customer data, confidential information, or material without redistribution rights.

## Local checks

Python 3.9 or newer, Bash, and Node.js 22 or newer are sufficient for these checks. Codex credentials and model calls are not required.

```bash
python3 -B -m unittest discover -s tests -v
node tests/browser_checks.js
bash -n vendor/ralph/ralph-loop.sh
git diff --check
```

The tests run the included Ralph script with a simulated agent process in temporary workspaces. They cover the local HTTP boundary, campaign flow, iteration limits, human decisions, artifact preservation, and browser helpers. They do not assess model quality or legal suitability of generated copy.

Keep reusable source, skills, prompts, and documentation in English. The supplied fictional case data and interface use Brazilian Portuguese. Preserve the distinction between synthetic persona perspectives, checking supplied rules, and human approval.

## Dependencies and licensing

The application uses the Python standard library and browser-native JavaScript. Add a runtime dependency only with a clear justification and compatible licensing. Preserve third-party notices. Changes to the included Ralph script must retain its attribution and identify modifications in the file.
