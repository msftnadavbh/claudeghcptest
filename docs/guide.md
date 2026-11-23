# Setup and configuration guide

This project configures a customer's installed Claude Desktop (macOS) to use GitHub Copilot inference through third-party Gateway mode. The normal mode updates only the `Claude-3p` config library in place. The optional isolated mode creates a separate test profile. The [validation record](validation.md) describes the scope and evidence for tested behavior.

## Setup

Requirements: macOS, Claude Desktop, Python 3 available as `python3`, GitHub CLI as `gh`, and a GitHub account with Copilot inference access. Keep the checkout in a stable location outside Desktop, Documents, Downloads, iCloud Drive, and CloudStorage because macOS privacy controls can block helper execution. Python must also be available to Desktop's helper environment.

Run `gh auth status --hostname github.com`. If needed, use `gh auth login --hostname github.com`; for multiple accounts, select the intended one with `gh auth switch --hostname github.com --user USERNAME`.

Quit Claude Desktop and run from the checkout:

```sh
./install
```

The installer checks authentication by running `gh auth token --hostname github.com` with output discarded. The check confirms token access, not Copilot inference entitlement. If executable discovery finds the wrong `gh`, use `./install --gh /absolute/path/to/gh`; the path must be absolute, executable, and outside macOS protected folders. Run `./install --help` for all options.

To inspect the exact proposed configuration, metadata, state, and paths without writing, run `./install --dry-run`. Dry-run still checks authentication, managed configuration, and whether Desktop is running. Keep Desktop closed until installation completes. Open it normally, choose **Continue** if prompted, then select a model.

The installer targets `~/Library/Application Support/Claude-3p/configLibrary`, the third-party config library derived from Desktop's default user-data directory plus `-3p`. It does not copy, move, or migrate first-party profile data, and does not change `claude_desktop_config.json`, `~/.claude`, or `~/.claude.json`.

### Refusal conditions

- Installation and removal refuse if the main Claude Desktop process is running against the default profile. The check recognizes renamed bundles and alternate installation paths; Helper-only processes are ignored. Ambiguous, unreadable, missing, repeated, or relative profile arguments fail closed. Explicit isolated processes using a different absolute `--user-data-dir` are allowed. The default base profile and its `-3p` variant are protected.
- Both commands refuse if system or per-user managed preferences contain `com.anthropic.claudefordesktop.plist`. Managed settings override the local library; contact your administrator. There is no force option.
- `HOME` must be the account home for normal customer installation.

## Configuration and backups

The default-mode library contains these files:

```text
configLibrary/<uuid>.json
configLibrary/_meta.json
configLibrary/.ghcp-state.json
```

The UUID JSON is rendered from [`config/ghcp.json`](../config/ghcp.json), with absolute helper paths substituted. `_meta.json` retains unrelated fields and entries; the installer adds or updates its marked GitHub Copilot entry and sets `appliedId`. Existing fields on that managed entry are preserved. Re-running `./install` updates the same owned UUID, refreshes helper paths, and supports upgrading older string-only model entries to tier metadata.

Versioned state records ownership, library identity, configuration hashes, previous selector (including whether it was absent), initial library/metadata shape, and the original backup pointer and timestamp. The installer will not adopt state by display name or migrate unsupported state. Removal validates state strictly; missing ownership markers, invalid/corrupt/copied state, or an edited/replaced owned config cause refusal with a backup recovery pointer. Preserve the state file while this installation is active.

Before each modifying operation on an existing library, the full library is copied to a private `0700` sibling staging directory and published as `configLibrary.backup-<UTC>`. Backup contents and directories are synchronized before staging is renamed; the parent is synchronized before state references the backup. Incomplete staging names use `.partial-<uuid>` and are not completed recovery sources. Backups accumulate on each install and uninstall and are never automatically pruned. They can contain sensitive settings from other providers. Unsupported entries and symlinks cause refusal.

Writes use private `0600` temporary files, flush and sync file contents, and atomically replace destinations. Operations lock the library and recheck process state, symlinks, and expected bytes before publications. Publication order makes install state and configuration durable before selecting the entry. Removal synchronizes selector changes and owned-file deletion before removing state. These ordered writes support retries after ordinary interruptions, but there is no all-or-nothing multi-file transaction or guarantee against power-loss/device failures. Abrupt termination can leave temporary files or partial backup directories; inspect them after recovery rather than deleting customer files automatically. A final interruption can leave an empty library directory.

There is a residual race: Desktop does not honor the installer lock, and checks cannot eliminate a concurrent launch, editor, or path replacement between verification and a write. Keep Desktop closed and avoid concurrent edits, automatic launches, or restarts throughout install/removal. If a snapshot or provenance mismatch occurs, inspect the backup; do not force an overwrite.

## How it works

### Gateway, credentials, and models

The configuration selects `inferenceProvider: "gateway"`, bearer authentication, and `inferenceCredentialKind: "helper-script"` at `https://api.githubcopilot.com` without `/v1`; Desktop sends Messages requests under `/v1/messages`. It starts the absolute `gh` executable with separate arguments `auth`, `token`, `--hostname`, `github.com`. The helper timeout is 60 seconds and token cache TTL is 3,600 seconds. Generated settings contain paths, not credentials. Shell `ANTHROPIC_BASE_URL` or Claude Code `apiKeyHelper` settings alone do not configure Desktop's provider.

Model discovery is disabled because the Copilot Anthropic-style `/v1/models` endpoint returns 404. The explicit `inferenceModels` list is:

| Model ID | Claude Code family metadata |
| --- | --- |
| `claude-opus-5.5` | `anthropicFamilyTier: "opus"`, `isFamilyDefault: true` |
| `claude-sonnet-5.5` | `anthropicFamilyTier: "sonnet"`, `isFamilyDefault: true` |
| `claude-haiku-5.5` | `anthropicFamilyTier: "haiku"`, `isFamilyDefault: true` |
| `claude-sonnet-5` | No family-default metadata |
| `claude-haiku-4.5` | No family-default metadata |

The three family defaults make Desktop's Code tab pin `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL` to the dotted IDs `claude-opus-5.5`, `claude-sonnet-5.5`, and `claude-haiku-5.5`. This is supplied through `inferenceModels`; do not add global Claude Code settings. Availability is account-dependent. Opus requests may receive GitHub Copilot HTTP 429 rate limits.

### Claude Code tab

The Code tab uses the same gateway configuration. The command table summarizes observed support for embedded Claude Code 2.1.330; command behavior can vary with later Desktop versions.

| Command or feature | Status and scope |
| --- | --- |
| `/btw` | Available from a Desktop conversation with **Cmd+;** side chat. It can use context from the main conversation. |
| `/insights` | Available for local usage analysis. Eligibility filters out short or warmup sessions; use substantive work sessions for a populated report. |
| `/model` | Switches among configured models. |
| `/compact`, `/context` | Available for conversation compaction and context information. |
| `/mcp`, `/status` | Available; Desktop can show the managed GitHub MCP connection. |
| `/cost` | Opens local usage information; it does not report Copilot billing costs. |
| `/effort`, `/config`, `/permissions`, `/memory`, `/resume` | Available for session effort and local Code settings/actions. |
| `/usage` | SDK-only in the tested engine; not verified as a Desktop command. |
| `/hooks` | Terminal-only; Desktop directs users to Claude Code in a terminal. |
| `/agents` | The old wizard has been removed in the tested embedded version. |
| Account and cloud-only commands | Unavailable because they require first-party identity or Anthropic-hosted cloud services. |

`/insights` analyzes local usage and only includes eligible sessions in its final report. A successful command does not mean every session is included. See [validation](validation.md#claude-code-tab) for surface-specific evidence.

### GitHub MCP server

`managedMcpServers` configures the managed HTTP server `github` at `https://api.githubcopilot.com/mcp/readonly`, with `X-MCP-Toolsets: web_search`. Desktop invokes the repository's `bin/ghcp-mcp-headers` helper, passing the absolute `gh` path; the helper returns an Authorization header at runtime. The connection and direct `web_search` tool call were tested. A web-search call initiated by a Desktop conversation has not been observed.

## Undo and uninstall

Quit Desktop and optionally preview the removal:

```sh
./uninstall --dry-run
./uninstall
```

Run `./uninstall --help` for available options. Removal deletes only the owned GitHub Copilot config file and metadata entry, preserving foreign entries and fields. It restores the prior `appliedId` only if GitHub Copilot is still selected. A later selection or deliberately absent selector is preserved. The old selection is restored only if its entry and config file still exist; otherwise `appliedId` remains absent rather than pointing to a missing configuration. If the library was created by this installation and is empty after removal, it is deleted. Backups remain.

There is no automatic full-backup restore option. For manual recovery, keep Desktop closed, preserve the current library separately, and restore only the intended `configLibrary` backup. Whole-library restoration discards later changes. Remove the checkout only after no installed configuration references its MCP helper. Uninstall does not revoke GitHub CLI authentication or delete conversations.

## Isolated testing

Use the optional mode for a separate test profile without changing the default-profile installation:

```sh
./install --isolated
# Or specify a separate profile directory:
./install --isolated "$HOME/claude-ghcp-test/Isolated-3p"
```

The default profile is `~/claude-ghcp-test/Isolated-3p`; custom profile directories must end in `-3p`. Real Claude Application Support profiles, shared Claude Code settings, and managed preferences are refused. Each isolated install creates a new UUID entry and backs up existing `_meta.json` when present. The legacy `scripts/install-isolated DIR` command remains available.

The lifecycle scripts expect the normal main Desktop at `/Applications/Claude.app` to remain running. Find its main process ID using Activity Monitor or `ps -axo pid,command`, then substitute it for `<normal-main-PID>`:

```sh
scripts/launch-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID>
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID> --dry-run
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID>
```

Launch passes `--user-data-dir=<profile>`, sets `CLAUDE_CONFIG_DIR=<profile>/claude-code`, removes inference-related environment overrides, and writes launcher output under the profile's `logs` directory. Stop selects exact isolated-profile processes, rechecks before signaling, and uses SIGTERM only; it does not force-kill. It also checks the protected normal process identity, start time, and config checksum. If Desktop does not exit, inspect the exact test instance and shut it down deliberately. Remove test profile data manually when no longer needed. Default `./uninstall` manages the default installation, not isolated profile cleanup.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Desktop-running refusal | Quit the normal main instance and retry; keep it closed until the command finishes. |
| Managed configuration refusal | Ask your administrator about managed Desktop preferences. |
| Authentication preflight fails | Sign in with `gh`, select the intended account, and check token environment overrides. |
| Helper works only in Terminal | Check absolute helper paths, executable permissions, Python availability, and macOS protected-folder restrictions. Re-run install after moving the checkout. |
| Empty model picker | Confirm the selected entry has the five full model IDs and `modelDiscoveryEnabled: false`. |
| Inference 401/403 | Check the active GitHub account and Copilot inference entitlement. |
| Inference 404 | Confirm the gateway base URL is `https://api.githubcopilot.com`, without `/v1`. |
| Opus HTTP 429 | Copilot may be rate limiting Opus. Retry later or select another configured model. |
| MCP connection failure | Check the managed server URL, helper path and arguments, and the `X-MCP-Toolsets: web_search` header. |
| State or snapshot refusal | Keep the backup; investigate changed metadata/configuration before retrying. Do not edit the state file to bypass validation. |

## Privacy, logs, and known limitations

Configuration rendering is local. GitHub CLI preflight output is discarded. Inference and MCP requests go to GitHub. Desktop also fetches a hosted model catalog and runtime components, so this is not GitHub-Copilot-only network traffic. Logs and conversations may contain sensitive content.

For default mode, the tested Desktop build writes logs under `~/Library/Logs/Claude-3p/`, including `main.log`. Logs may be shared at the OS account level, and the optional isolated profile is not a complete security boundary; Desktop may share logs or Keychain state.

Backups of an existing library accumulate on each modifying run and are not automatically pruned. The installer has residual races because Desktop does not honor its lock; do not run it while Desktop or another config editor can change the target. Tested versions are Claude Desktop **6.28899.6** and embedded Claude Code **2.1.330**. Other versions may behave differently. Server-side Auto-mode checks must remain disabled: GitHub Copilot rejects the `safeguards` field when those checks are enabled. Long-running sessions, credential refresh after expiry, large-context behavior, Cowork, and Desktop-conversation-initiated web search remain unverified. A populated Desktop Code `/insights` report has not been observed; the command's eligibility behavior is documented above.

## References

- [Desktop gateway configuration](https://claude.com/docs/third-party/claude-desktop/gateway)
- [Desktop configuration reference](https://claude.com/docs/third-party/claude-desktop/configuration)
- [Desktop credential helpers](https://claude.com/docs/third-party/claude-desktop/credential-helper)
- [GitHub CLI authentication](https://cli.github.com/manual/gh_auth)
