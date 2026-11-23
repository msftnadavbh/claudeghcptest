# Working on this repository

This installer configures Claude Desktop on macOS to use GitHub Copilot for inference. Desktop calls GitHub CLI for credentials at runtime.

Run `python3 -B -m unittest discover -s tests -v` from the repository root. The suite uses only the Python standard library and Git. Keep tests hermetic: use a temporary `HOME`, a fake `gh`, and mocked process lists and signals. Tests must never contact the network or invoke the real `gh`.

- Never run `./install` or `./uninstall` against a real `HOME`. For manual checks, prefer `--dry-run` with `--sandbox-home` under a fresh temporary `HOME`.
- Never launch Claude Desktop in CI.
- Never add tokens to code, configuration, fixtures, or logs.
