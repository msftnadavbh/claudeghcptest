<p align="center"><strong>Claude Desktop on GitHub Copilot</strong> runs Claude Desktop through GitHub Copilot inference, using your GitHub CLI sign-in.</p>
<p align="center">Your installed Claude Desktop. Runtime credentials. Five Claude models.</p>
<p align="center"><a href="#quickstart"><strong>Quickstart</strong></a> · <a href="docs/guide.md">Documentation</a> · <a href="docs/validation.md">Test results</a></p>

---

## Quickstart

You need macOS, Claude Desktop, Python 3 (tested with 3.15), and GitHub CLI signed in to an account with Copilot inference access. Keep this checkout outside Desktop, Documents, Downloads, and cloud-synced folders. Run the commands from the checkout; the [setup guide](docs/guide.md#setup) explains prerequisites.

1. **Check your sign-in.** Run `gh auth status --hostname github.com`. If needed, run `gh auth login --hostname github.com` and choose the account you want to use.
2. **Quit Claude Desktop and install.** Run `./install`. It checks your sign-in, backs up the existing config library, and selects GitHub Copilot for your installed Desktop.
3. **Open Claude Desktop.** It starts in third-party mode on GitHub Copilot. Choose **Continue** if prompted, select a model, and chat.

Use `./install --dry-run` to preview changes or `./install --help` for options. Keep Claude closed until installation finishes.

## Use your existing sign-in

**Gateway mode** sends inference to `https://api.githubcopilot.com` with bearer authentication. Desktop runs the absolute `gh` executable with a separate argument list to obtain credentials at runtime. Setup stores helper paths, not a token. There is no inference proxy or credential wrapper to keep running.

## Choose a model and connect GitHub

**The model picker** offers Opus 5.5, Sonnet 5.5, Haiku 5.5, Sonnet 5, and Haiku 4.5. The list is explicit because Copilot's Anthropic-style model discovery endpoint returns 404. All five IDs passed direct Messages API checks; an isolated Desktop conversation completed with Opus 5.5.

**GitHub MCP** connects to the read-only endpoint with a runtime headers helper and the `web_search` toolset. The Desktop connection and a direct web-search tool call passed. A web-search call initiated by a Desktop conversation has not yet been observed. See [test results](docs/validation.md) for the distinction between Desktop checks and direct API probes.

## Privacy and safety

Configuration rendering is local. Installation checks GitHub CLI credentials with output discarded; normal inference and MCP use send requests to GitHub. Desktop also fetches a hosted model catalog and runtime components, so **this is not a GHCP-only network configuration**. Credentials are not written into generated configuration, but conversations and application diagnostics can contain sensitive content.

**Small, reversible configuration changes.** The installer changes only the `configLibrary` inside `~/Library/Application Support/Claude-3p`, with timestamped sibling backups. It preserves foreign entries and remembers the previous selection. Your first-party `Claude` profile, `claude_desktop_config.json`, and Claude Code settings are untouched. Managed (MDM) configurations cause installation to refuse. Running-app checks are snapshots: do not launch Desktop or edit its configuration during installation or removal. [The guide](docs/guide.md#privacy-and-network-boundaries) explains this residual race and the storage boundaries.

## Undo and uninstall

Quit Claude Desktop, run **`./uninstall`**, then reopen it. This removes the entry created by this installer, preserves any later selection, and otherwise restores the previous selection if it still exists. Use `./uninstall --dry-run` to preview.

Keep the checkout while Desktop uses its helper. See [undo and uninstall](docs/guide.md#undo-and-uninstall) for backups and cleanup.

## Optional isolated test profile

For testing alongside your normal app, use `./install --isolated [DIR]`. The default test directory is `~/claude-ghcp-test/Isolated-3p`; custom names must end in `-3p`. See the [isolated launch and stop instructions](docs/guide.md#isolated-testing).

<details>
<summary>Platform and version details</summary>

Live checks used Claude Desktop **6.28899.6** on macOS with embedded Claude Code **2.1.330**. Default installation supports Desktop bundles in different locations; isolated lifecycle helpers target `/Applications/Claude.app`. Windows and Linux have not been tested. Python and GitHub CLI must also be available to Desktop's helper environment. Re-run installation if you move the checkout.

**Server-side Auto mode checks** are disabled in the supplied configuration. Full safeguards compatibility, long sessions, credential refresh, and the separate Code and Cowork tabs remain untested. See [known limitations](docs/guide.md#known-limitations).

</details>

## Documentation

- [Setup, configuration, and troubleshooting](docs/guide.md)
- [Validation record and test coverage](docs/validation.md)
- [Configuration template](config/ghcp.json)

## Development

The tooling uses Python's standard library. Offline tests use synthetic credentials, a temporary HOME for every test, sanitized subprocess environments, and a test-only guard against real-profile I/O.

| Location | Purpose |
| --- | --- |
| `install`, `uninstall` | Customer entry points: configure installed Desktop and revert |
| `scripts/config_modes.py` | Default-mode config-library merge, backups and guards |
| `config/ghcp.json` | Flat Desktop gateway and MCP configuration template |
| `bin/ghcp-mcp-headers` | Runtime JSON headers helper for GitHub MCP |
| `scripts/desktop.py` | Configuration rendering and isolated lifecycle utilities |
| `scripts/render-config`, `scripts/install-isolated` | Render paths and install a separate config library |
| `scripts/launch-isolated`, `scripts/stop-isolated` | Start and stop the isolated app |
| `scripts/live-check.py` | Explicit live probes and masked evidence capture |
| `tests/` | Offline tests and test-process safety guard |
| `docs/` | User guide and validation summary |

Maintainers need Python 3 (tested with 3.15) and Git for the offline suite; live validation additionally needs macOS, Claude Desktop, and an authorized GitHub CLI account. Run `python3 -B -m unittest discover -s tests -v` before submitting changes. Keep local profiles, raw diagnostic captures, credentials, and machine-specific inventories out of commits.
