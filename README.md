<p align="center"><strong>Claude Desktop on GitHub Copilot</strong> runs Claude Desktop through GitHub Copilot inference, using your GitHub CLI sign-in.</p>
<p align="center">A separate profile. Runtime credentials. Five Claude models.</p>
<p align="center"><a href="#quickstart"><strong>Quickstart</strong></a> · <a href="docs/guide.md">Documentation</a> · <a href="docs/validation.md">Test results</a></p>

---

## Quickstart

You need macOS, Claude Desktop installed in **Applications**, Python 3 (tested with 3.15), and GitHub CLI signed in to an account with Copilot inference access. Keep this checkout outside Desktop, Documents, Downloads, and cloud-synced folders. Run the commands from the checkout; the [setup guide](docs/guide.md#setup) explains prerequisites and process selection.

1. **Check your sign-in.** Run `gh auth status --hostname github.com`. If needed, run `gh auth login --hostname github.com` and choose the account you want to use.
2. **Prepare a separate profile.** Run `scripts/install-isolated "$HOME/claude-ghcp-test/Isolated-3p"`. Setup resolves the helper paths, checks that the active account can supply a token, and writes the configuration into that profile.
3. **Open and chat.** Find the PID of your normal Claude main process, then run `scripts/launch-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <PID of your normal Claude>`, replacing the placeholder with its number. In the new window, choose **Continue**, select a model, and send a message.

The launch command prints the new instance's PID. The normal app stays running alongside it. The isolated profile name must end in **`-3p`**; the scripts refuse the normal Claude Application Support profile locations.

## Use your existing sign-in

**Gateway mode** sends inference to `https://api.githubcopilot.com` with bearer authentication. Desktop runs the absolute `gh` executable with a separate argument list to obtain credentials at runtime. Setup stores helper paths, not a token. There is no inference proxy or credential wrapper to keep running.

## Choose a model and connect GitHub

**The model picker** offers Opus 5.5, Sonnet 5.5, Haiku 5.5, Sonnet 5, and Haiku 4.5. The list is explicit because Copilot's Anthropic-style model discovery endpoint returns 404. All five IDs passed direct Messages API checks; an isolated Desktop conversation completed with Opus 5.5.

**GitHub MCP** connects to the read-only endpoint with a runtime headers helper and the `web_search` toolset. The Desktop connection and a direct web-search tool call passed. A web-search call initiated by a Desktop conversation has not yet been observed. See [test results](docs/validation.md) for the distinction between Desktop checks and direct API probes.

## Privacy and safety

Configuration rendering is local. Installation checks GitHub CLI credentials with output discarded; normal inference and MCP use send requests to GitHub. Desktop also fetches a hosted model catalog and runtime components, so **this is not a GHCP-only network configuration**. Credentials are not written into generated configuration, but conversations and application diagnostics can contain sensitive content.

**A separate profile is not a complete security boundary.** The tested build shares `~/Library/Logs/Claude/` with the normal app and may share OS-level state such as Keychain items. Lifecycle guards check the normal app's PID/start time and one configuration-file checksum; they do not inventory the normal profile. No script applies configuration to, backs up, or restores your real profile. [The guide](docs/guide.md#privacy-and-network-boundaries) describes the boundaries and diagnostics.

## Undo and uninstall

Run `scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <PID of your normal Claude> --dry-run` to inspect the isolated process selection. Remove `--dry-run` to stop it. The command signals only matching isolated Claude processes; it does not quit every instance by application name.

After stopping the isolated instance, remove its profile folder if you no longer need its conversations and settings. You can then remove this checkout. If you manually applied the configuration to your normal app, restore only your saved **configLibrary** folder while Claude is closed. See [undo and uninstall](docs/guide.md#undo-and-uninstall).

<details>
<summary>Platform and version details</summary>

Live checks used Claude Desktop **6.28899.6** on macOS with embedded Claude Code **2.1.330**. The scripts target macOS and `/Applications/Claude.app`; Windows and Linux have not been tested. Python and GitHub CLI must also be available to Desktop's helper environment. Absolute helper paths need regenerating if you move the checkout.

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
| `config/ghcp.json` | Flat Desktop gateway and MCP configuration template |
| `bin/ghcp-mcp-headers` | Runtime JSON headers helper for GitHub MCP |
| `scripts/desktop.py` | Configuration rendering and isolated lifecycle utilities |
| `scripts/render-config`, `scripts/install-isolated` | Render paths and install a separate config library |
| `scripts/launch-isolated`, `scripts/stop-isolated` | Start and stop the isolated app |
| `scripts/live-check.py` | Explicit live probes and masked evidence capture |
| `tests/` | Offline tests and test-process safety guard |
| `docs/` | User guide and validation summary |

Maintainers need Python 3 (tested with 3.15) and Git for the offline suite; live validation additionally needs macOS, Claude Desktop, and an authorized GitHub CLI account. Run `python3 -B -m unittest discover -s tests -v` before submitting changes. Keep local profiles, raw diagnostic captures, credentials, and machine-specific inventories out of commits.
