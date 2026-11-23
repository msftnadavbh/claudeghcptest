<p align="center"><strong>Claude Desktop on GitHub Copilot</strong> runs your installed Claude Desktop through GitHub Copilot inference.</p>
<p align="center"><a href="#quickstart"><strong>Quickstart</strong></a> · <a href="docs/guide.md">Guide</a> · <a href="docs/validation.md">Validation</a></p>
<p align="center"><a href="https://github.com/msftnadavbh/claudeghcptest/actions/workflows/tests.yml"><img alt="Tests on main" src="https://github.com/msftnadavbh/claudeghcptest/actions/workflows/tests.yml/badge.svg?branch=main"></a></p>

## Quickstart

Requires macOS, Claude Desktop, Python 3, GitHub CLI (`gh`), and an account with Copilot inference access. Keep this checkout in a stable location outside Desktop, Documents, Downloads, and cloud-synced folders.

1. **Sign in to GitHub.** Run `gh auth status --hostname github.com`; if needed, sign in with `gh auth login --hostname github.com` and choose the account with Copilot access.
2. **Quit Claude Desktop and install.** From this checkout run `./install`. It checks GitHub CLI authentication, backs up an existing `configLibrary`, and configures the GitHub Copilot entry in your installed Desktop's third-party profile.
3. **Open Claude Desktop.** Choose **Continue** if prompted, select a model, and start a conversation.

Use `./install --dry-run` to preview planned changes. Keep Desktop closed until installation finishes. See the [setup guide](docs/guide.md#setup) for prerequisites and safeguards.

## Use your GitHub sign-in

**Runtime credentials.** Desktop obtains a GitHub token by running your absolute `gh` executable when needed. The configuration stores helper paths, not a token; no inference proxy or credential wrapper needs to run.

**Five models.** The model picker offers Opus 5.5, Sonnet 5.5, Haiku 5.5, Sonnet 5, and Haiku 4.5. Model availability depends on your account and may change.

**GitHub MCP.** A managed GitHub MCP server exposes the `web_search` toolset through a runtime headers helper.

## Claude Code tab

**Model defaults.** Tier metadata for Opus, Sonnet, and Haiku 5.5 pins the Code tab defaults to their dotted GitHub Copilot model IDs.

**Commands.** `/btw` opens a side chat with Cmd+;. `/insights` analyzes eligible local work sessions. `/model`, `/compact`, `/context`, `/mcp`, `/status`, `/cost`, `/effort`, `/config`, `/permissions`, `/memory`, and `/resume` are available. `/usage` is SDK-only; `/hooks` is terminal-only; the old `/agents` wizard has been removed. Account and cloud-only commands are unavailable. Opus can encounter GitHub Copilot HTTP 429 rate limits. See the [command and validation details](docs/guide.md#claude-code-tab).

## Privacy and safety

Configuration rendering is local. Inference and MCP requests go to GitHub, and Desktop also fetches a hosted model catalog and runtime components, so network traffic is not limited to GitHub Copilot. Conversations and application diagnostics can contain sensitive content.

**Scoped changes.** Default installation changes only `configLibrary` under `~/Library/Application Support/Claude-3p`. It makes private, timestamped backups, preserves other entries and metadata, and records recovery state. It does not change the first-party `Claude` profile or Claude Code settings. Default-mode installation refuses while Desktop is running or when managed (MDM) configuration exists. Isolated mode does not check for MDM configuration; where `com.anthropic.claudefordesktop` managed settings exist under `/Library/Managed Preferences`, Desktop's managed tier takes precedence and isolated testing is not meaningful. See [configuration and backups](docs/guide.md#configuration-and-backups) and [isolated testing](docs/guide.md#isolated-testing).

## Undo and uninstall

Quit Claude Desktop and run `./uninstall`. It removes only the GitHub Copilot entry and files. If GitHub Copilot remains selected, it restores the prior selection only when that entry and its file still exist; a later selection is kept. Backups remain available. Keep the checkout while Desktop uses its helper. See [undo and uninstall](docs/guide.md#undo-and-uninstall).

## Optional isolated test profile

For a separate test profile alongside normal Desktop, use `./install --isolated [DIR]`. The default is `~/claude-ghcp-test/Isolated-3p`; a custom directory must end in `-3p`. See [isolated testing](docs/guide.md#isolated-testing) for launch and stop instructions.

<details>
<summary>Platform and version details</summary>

Live checks used Claude Desktop **6.28899.6** on macOS with embedded Claude Code **2.1.330**. Default mode configures the installed Desktop in place. The optional isolated launch/stop helpers target `/Applications/Claude.app`. Windows and Linux are not supported or tested for Desktop operation. Re-run `./install` if the checkout moves so absolute helper paths are refreshed.

</details>

## Documentation

- [Setup, configuration, both modes, commands, troubleshooting, and limitations](docs/guide.md)
- [Validation record and contributor test instructions](docs/validation.md)
- [Configuration template](config/ghcp.json)

## Development

The tooling uses Python's standard library. Run the offline suite with `python3 -B -m unittest discover -s tests -v`. CI runs it on macOS and Ubuntu and checks tracked files for personal paths and credential patterns. Copilot coding agent setup steps install Python 3.12; repository-specific instructions are in [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

| Location | Purpose |
| --- | --- |
| `install`, `uninstall` | Customer entry points for default-profile setup and removal |
| `scripts/config_modes.py` | Default-mode merge, backup, state validation, and guards |
| `config/ghcp.json` | Gateway models and managed GitHub MCP template |
| `bin/ghcp-mcp-headers` | Runtime JSON headers helper for GitHub MCP |
| `scripts/desktop.py` | Rendering and isolated-profile lifecycle utilities |
| `scripts/render-config`, `scripts/install-isolated` | Render configuration and install a separate profile |
| `scripts/launch-isolated`, `scripts/stop-isolated` | Launch and stop the isolated app |
| `scripts/live-check.py` | Opt-in live probes and masked evidence collection |
| `tests/` | Offline tests and test-only profile-I/O guard |
| `docs/` | Customer guide and validation record |
