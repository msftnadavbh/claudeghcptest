# Setup and configuration guide

Switch your installed Claude Desktop to **third-party Gateway mode** using GitHub Copilot inference and your GitHub CLI sign-in. The [validation record](validation.md) distinguishes tested behavior from remaining limitations.

## Setup

You need macOS, Claude Desktop, Python **3 (tested with 3.15)** as `python3`, and GitHub CLI as `gh`, with Copilot inference access. Keep this checkout in a stable location such as `~/src/claude-ghcp-desktop`, outside Desktop, Documents, Downloads, iCloud Drive and CloudStorage: macOS privacy controls can block helpers there. Python must be available to Desktop's helper environment as well as your terminal.

### 1. Select your GitHub account

Run `gh auth status --hostname github.com`. If needed, sign in with `gh auth login --hostname github.com`. For multiple accounts:

```sh
gh auth switch --hostname github.com --user YOUR_GITHUB_USERNAME
```

The installer resolves an absolute executable path and checks `gh auth token --hostname github.com`, discarding stdout and stderr. Environment-token overrides still apply. Token retrieval does not prove inference entitlement. You can override executable discovery with `./install --gh /absolute/path/to/gh`.

### 2. Quit Desktop and install

From the checkout, run:

```sh
./install
```

To see the planned paths, backup, complete configuration, merged metadata, and state without writing, use `./install --dry-run`. Dry-run still checks process state, MDM and authentication. Both entry points offer `--help`.

Only `~/Library/Application Support/Claude-3p/configLibrary` is configured. Desktop derives that location from its default user-data directory (`Claude`) plus `-3p`. The installer does not move, copy or replace your profile; it does not change the first-party `Claude` folder, either `claude_desktop_config.json`, `~/.claude`, or `~/.claude.json`. First-party history is not migrated into third-party mode.

The installer refuses while a main Desktop process uses the default profile. It recognizes main executables in `/Applications`, your Applications folder, and renamed bundles or other installation locations. Explicit isolated instances using a different absolute `--user-data-dir` are allowed. Missing, repeated, relative or unreadable profile arguments fail closed; Helper-only process rows are ignored. Both the base default user-data path and its `-3p` variant are protected, including case aliases.

**MDM:** Installation and removal refuse if `/Library/Managed Preferences/com.anthropic.claudefordesktop.plist` or the corresponding per-user managed plist exists. Those settings override the local library; contact your administrator. There is no force override.

### 3. Open Desktop

Open Claude Desktop normally. It starts in third-party mode on GitHub Copilot. Choose **Continue** if prompted, pick a model and chat. Keep this checkout in place because its MCP helper is referenced by absolute path. Re-running `./install` updates this installer's existing UUID instead of adding another entry.

## Configuration and backups

The library contains:

```text
configLibrary/<uuid>.json
configLibrary/_meta.json
configLibrary/.ghcp-state.json
```

The UUID file contains flat settings rendered from `config/ghcp.json`. The installer preserves existing metadata fields and entries, adds or updates its GitHub Copilot entry, and selects it with `appliedId`. Existing fields on that entry are also preserved. Versioned state records its UUID, a matching metadata ownership marker, the canonical library path, known configuration hashes, the original selector (including whether it was absent), whether the library and metadata existed, the original backup path and UTC timestamp. UI entry renames and deletion are supported; a replaced/edited owned file, missing ownership marker, or corrupt/incomplete/copied/older-version state causes a clear refusal with a backup recovery pointer. State is not adopted by display name or silently migrated from older schemas. Do not edit or delete state while the installation is active; use config-library-only backup recovery if it is damaged.

Before each modifying operation on an existing library, the whole small library is copied into a private `0700` sibling staging directory. Backup files and directories are fsynced before staging is renamed to `configLibrary.backup-<UTC>`, then the parent directory is fsynced before state references that backup. A `.partial-<uuid>` suffix marks an incomplete backup, never a completed recovery source; caught copy/sync failures remove staging. If the library was absent, state records that fact. Backups accumulate and are never automatically pruned. They may contain sensitive settings from other providers; keep them private and delete old backups deliberately when no longer needed. They are not whole-profile backups. Unsupported backup entries and symlinks cause refusal.

JSON publication uses private `0600` temporary files, flush/fsync, and atomic replacement; caught serialization, sync and replacement failures clean up the temporary file. The library, metadata, state, owned configuration and their ancestors must not be symlinks. Installer/remover operations lock the library directory and recheck the running app and expected state/config/metadata bytes immediately before each publication, rejecting stale snapshots.

**Interruption recovery:** Installation fsyncs the library directory after publishing state, then after publishing the configuration, then after selecting it in metadata. Thus recovery state and config are ordered before the selector, subject to the filesystem/device honoring fsync. On removal, the selector change is synchronized first, then the owned-file deletion; state is retained until both are durable, then its removal is synchronized. An ordinary interruption between completed steps can be recovered by rerunning installation or removal while Desktop is closed. Missing owned files are supported and retries reuse the owned UUID. Tests inject failures and assert synchronization order; they do not simulate power loss or prove hardware persistence. There is no all-or-nothing multi-file transaction. Abrupt process death can leave private JSON temp files or partial backup directories: inspect and remove those explicitly after recovery rather than deleting arbitrary customer files automatically. A final interrupted empty-directory cleanup can leave an empty library.

**Residual race:** Desktop does not honor the installer's lock. Repeated running-app, symlink and byte-snapshot checks narrow but cannot eliminate a launch/editor/path-replacement race between a check and a write. Keep Desktop closed and avoid concurrent editors, automatic launches and restarts until the command finishes. If a snapshot/provenance mismatch is reported, inspect the retained backup instead of forcing an overwrite.

## How it works

### Gateway and runtime credentials

The base URL is `https://api.githubcopilot.com`, without `/v1`; Desktop appends `/v1/messages`. The configuration selects `inferenceProvider: "gateway"`, bearer authentication and `inferenceCredentialKind: "helper-script"`. Desktop spawns the absolute `gh` executable with `['auth', 'token', '--hostname', 'github.com']`. There is no inference proxy or shell credential wrapper. The helper timeout is 60 seconds and cache TTL is 3,600 seconds. Generated settings contain paths rather than tokens.

Setting `ANTHROPIC_BASE_URL` in a shell or Claude Code's `apiKeyHelper` alone does not select Desktop's provider. The scripts do not install any Claude Code settings.

### Models

Provider discovery is disabled because Copilot's Anthropic-style `/v1/models` endpoint returns 404. The explicit list is:

| Model ID | Picker display observed |
| --- | --- |
| `claude-opus-5.5` | claude-opus-5.5 |
| `claude-sonnet-5.5` | claude-sonnet-5.5 |
| `claude-haiku-5.5` | claude-haiku-5.5 |
| `claude-sonnet-5` | Sonnet 5 |
| `claude-haiku-4.5` | claude-haiku-4.5 |

All five IDs passed direct Messages requests; only Opus 5.5 was exercised in a Desktop conversation. Availability depends on your account and can change.

### GitHub MCP

The managed HTTP server `github` uses `https://api.githubcopilot.com/mcp/readonly` and `X-MCP-Toolsets: web_search`. Desktop runs `bin/ghcp-mcp-headers` with the absolute `gh` path as its argument. It emits a JSON Authorization header and a fixed error if credentials cannot be obtained. Desktop accepted the local library as a managed source and connected with `auth: 'headers-helper'`. Direct web search passed; a Desktop-conversation-initiated search remains unobserved.

## Undo and uninstall

Quit Desktop and run:

```sh
./uninstall --dry-run
./uninstall
```

Removal deletes this installer's UUID file and entry and preserves foreign entries and fields, including ones added later. It restores the original `appliedId` **only if the current selector still points to this installer's UUID**. A later foreign selection or deliberately cleared selector is preserved. Restoration requires the original entry and its configuration file still to exist; otherwise the selector is left absent and a clear note is printed, never a dangling original ID. An originally empty/absent selector also becomes absent. If the library was created by the installer and has become empty, it is removed. Backups remain. A previously absent selector does not imply all third-party mode inputs elsewhere have been removed.

There is no automatic whole-backup restore flag. For manual recovery, keep Desktop closed, inspect the backup path recorded in state, retain the current library separately, and restore **only the configLibrary folder** you intend to recover. Full-folder restoration intentionally discards changes made after that backup; ordinary `./uninstall` preserves other entries instead.

Remove the checkout only after no installed configuration references its helper. Removing files does not revoke GitHub authentication or delete Desktop conversations.

## Isolated testing

This secondary testing mode preserves the original separate-profile installation behavior:

```sh
./install --isolated
# Or choose a directory:
./install --isolated "$HOME/claude-ghcp-test/Isolated-3p"
```

The optional directory defaults to the path above and must end in `-3p`; normal Application Support Claude profiles and shared Claude Code configuration locations are refused. The legacy `scripts/install-isolated DIR` remains available. Unlike default mode, each isolated installation creates a new UUID, appends it to metadata and saves a metadata backup only if `_meta.json` already exists.

For lifecycle helpers, Desktop must be installed at `/Applications/Claude.app`, with your normal main instance already running. Find its PID in Activity Monitor or `ps -axo pid,command`; choose the main executable, not a Helper. Replace the placeholder:

```text
scripts/launch-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID>
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID> --dry-run
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <normal-main-PID>
```

Launch uses `--user-data-dir=<profile>` and `CLAUDE_CONFIG_DIR=<profile>/claude-code`, strips inference environment overrides and prints the new main PID. Stop rechecks exact profile matches immediately before SIGTERM; it never force-kills. Guards compare the protected main PID/start time and one configuration-file checksum. After stopping, remove the test profile if its data is no longer needed. Default `./uninstall` is for the default installation, not isolated profile deletion.

Desktop may ignore SIGTERM while a fresh profile is on its welcome screen. The shipped stop helper reports remaining processes instead of force-killing; verify the exact test instance before any manual shutdown. The supervised validation harness's separately authorized main-PID fallback is described in the [validation record](validation.md#default-mode-sandbox-validation).

## Privacy and network boundaries

Rendering is local; installation checks GitHub CLI credentials with output discarded. Inference and MCP send requests to GitHub. Desktop also refreshes a hosted model catalog and downloads runtime components, so this is **not GHCP-only network routing**.

For the normal Desktop's third-party mode, look for startup diagnostics in **`~/Library/Logs/Claude-3p/main.log`**. A base user-data directory without a `-3p` suffix caused the tested build to select this log directory; the existing isolated launch with an already-suffixed directory used `~/Library/Logs/Claude/main.log` instead.

Isolated profiles are not complete security boundaries. Those log directories are shared at the OS account level, and Desktop may also share Keychain state. Launcher stdout/stderr goes under the isolated profile's `logs` folder. Shared logs are not generally process-scoped; correlate timestamps and session details before drawing conclusions or sharing evidence. Neither the normal-profile checksum guard nor the sandbox validation inventories all profile files.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Quit Desktop refusal | Quit the normal main instance and retry; leave it closed throughout the operation. |
| Managed configuration refusal | Ask your administrator about the managed configuration. |
| Authentication preflight fails | Sign in with `gh`, select the intended account and check token environment overrides. |
| Helper works only in Terminal | Check absolute paths, executable permissions, Python availability and protected-folder restrictions. |
| Empty picker | Check the selected UUID, five full model IDs and `modelDiscoveryEnabled: false`. |
| Inference 401/403 | Check Copilot entitlement and the active GitHub account. |
| Messages 404 | Use the gateway root URL without `/v1`. |
| MCP fails | Check helper arguments, read-only URL, static toolset header and connection logs. |
| Paths changed | Re-run `./install` to refresh absolute helper paths. |

## Known limitations

Provider-side Auto mode checks are disabled (`inferenceGatewayAutoModeServerChecks: false`). A beta-header-only request does not establish full safeguards compatibility. Long sessions, credential refresh, large contexts, Desktop-initiated web search, and separate Code and Cowork tab workflows remain untested. The supported configuration is based on the tested Desktop version and may need updating as Desktop changes.

## References

- [Desktop gateway configuration](https://claude.com/docs/third-party/claude-desktop/gateway)
- [Desktop configuration reference](https://claude.com/docs/third-party/claude-desktop/configuration)
- [Desktop credential helpers](https://claude.com/docs/third-party/claude-desktop/credential-helper)
- [GitHub CLI authentication](https://cli.github.com/manual/gh_auth)
