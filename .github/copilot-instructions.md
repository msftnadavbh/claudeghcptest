# Working on this repository

This installer configures Claude Desktop on macOS to use GitHub Copilot for inference. Desktop calls GitHub CLI for credentials at runtime. Default mode edits only the third-party `configLibrary`; isolated mode creates a separate test profile.

Run `python3 -B -m unittest discover -s tests -v` from the repository root. The suite uses only the Python standard library and Git. Keep tests hermetic: use a temporary `HOME`, a fake `gh`, sanitized subprocess environments, and mocked process lists and signals. Tests must never contact the network or invoke the real `gh`.

- Never run `./install` or `./uninstall` against a real `HOME`. For manual checks, use a fresh temporary `HOME`, `GHCP_TEST_FORBID_REAL_HOME=1`, and `--sandbox-home`; prefer `--dry-run` with a fake executable supplied through `--gh`. The `GHCP_TEST_HOME` exception is test-only and works only when it exactly matches `HOME` and the real-HOME guard is enabled.
- Never launch Claude Desktop in CI or as part of the offline test suite.
- Never access `~/Library/Application Support/Claude*`, `~/.claude`, or `~/.claude.json` in tests or manual checks.
- Never add tokens to code, configuration, fixtures, or logs.
