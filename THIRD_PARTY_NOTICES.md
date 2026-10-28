# Third-party notices

## Ralph

`vendor/ralph/ralph-loop.sh` is based on [Ralph by César Gallego Rodríguez](https://gitlab.com/gallego.cesar/ralph).

Copyright (c) 2026 César Gallego Rodríguez. Licensed under Apache-2.0. The original author's attribution and repository reference are preserved in the included [notice](vendor/ralph/NOTICE), alongside the [license](vendor/ralph/LICENSE).

The included script has a compatibility modification: the optional command prefix uses `env` when no memory limiter applies, supporting Bash 3.2 with `set -u`. The modified file identifies this change.

## External runtime tools

Python and Codex CLI are installed separately. Their executables, credentials, model weights, and model services are not distributed in this repository. Their respective licenses and service terms apply independently.
