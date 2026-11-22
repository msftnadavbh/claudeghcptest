# Setup and configuration guide

This project configures Claude Desktop's **third-party Gateway mode** to use GitHub Copilot inference. It prepares a separate local profile and obtains credentials from GitHub CLI at runtime. The [validation record](validation.md) distinguishes tested behavior from remaining limitations.

## Setup

Install Claude Desktop at `/Applications/Claude.app`, Python **3 (tested with 3.15)** as `python3`, and GitHub CLI as `gh`. All executable Python entry points use `#!/usr/bin/env python3`. Desktop augments its helper PATH with the login-shell PATH and common installation locations, including Homebrew; Python must be available there as well as in your terminal.

Keep this checkout in a stable location, such as `~/src/claude-ghcp-desktop`, outside Desktop, Documents, Downloads, iCloud Drive, and CloudStorage. macOS privacy controls can block helpers in protected folders. Rendering rejects recognized protected helper locations. Moving the checkout later requires reinstalling the configuration because helper paths are absolute.

### 1. Select your GitHub account

```sh
gh auth status --hostname github.com
```

If you are not signed in, use `gh auth login --hostname github.com`. With multiple accounts, select the intended active account:

```sh
gh auth switch --hostname github.com --user YOUR_GITHUB_USERNAME
```

The helper uses `gh auth token --hostname github.com`, which selects the active account. GitHub CLI environment-token overrides also apply. The installer runs this same token command with stdout and stderr discarded before writing any configuration. It does not reject an otherwise working active account because another stored account fails `gh auth status`. Retrieving a token does not prove that the account has Copilot inference entitlement; a real request is needed to establish that.

### 2. Prepare an isolated profile

From the checkout:

```sh
scripts/render-config
scripts/install-isolated "$HOME/claude-ghcp-test/Isolated-3p"
```

Rendering prints valid JSON with resolved absolute paths and does not obtain credentials. Pass `--gh /absolute/path/to/gh` to rendering or installation if you need to override executable discovery. Installation checks the credential command, creates a new configuration UUID, preserves existing library entries, and saves a metadata backup **only when `_meta.json` already exists**, before selecting the new entry.

The profile name must end in **`-3p`**. Choose a directory outside the normal `~/Library/Application Support/Claude*` profiles and shared Claude Code configuration. The isolated-path guards reject those profile locations and resolved symlink aliases.

### 3. Launch alongside your normal app

The lifecycle tools require an already-running normal Claude main process to protect. Find its PID using Activity Monitor or `ps -axo pid,command`. Identify the main `/Applications/Claude.app/Contents/MacOS/Claude` process, not a Helper or your isolated process. Replace the placeholder below with that PID:

```text
scripts/launch-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <PID of your normal Claude>
```

The command prints the new main PID and launches Desktop directly with `--user-data-dir=<profile>` and `CLAUDE_CONFIG_DIR=<profile>/claude-code`. In the new instance's gateway welcome screen, choose **Continue**, then send a short chat. Its default model is `claude-opus-5.5`.

Use the exact PID and window identity when automating the UI; application name and bundle ID are shared by both instances. Do not send input to an unverified window. The launcher checks the protected process/start time and the checksum of `~/Library/Application Support/Claude-3p/claude_desktop_config.json`, if present. It does not walk either real profile tree.

## How it works

### Gateway mode

`config/ghcp.json` supplies flat Desktop configuration keys. The base URL is **`https://api.githubcopilot.com`**, without `/v1`. Desktop adds the API path, so inference reaches `/v1/messages`; bearer authentication is required.

```json
{
  "inferenceProvider": "gateway",
  "inferenceGatewayBaseUrl": "https://api.githubcopilot.com",
  "inferenceGatewayAuthScheme": "bearer",
  "inferenceCredentialKind": "helper-script",
  "inferenceCredentialHelper": "/absolute/path/to/gh",
  "inferenceCredentialHelperArgs": ["auth", "token", "--hostname", "github.com"],
  "inferenceGatewayAutoModeServerChecks": false
}
```

This is Desktop configuration. Setting `ANTHROPIC_BASE_URL` in your shell or configuring Claude Code's `apiKeyHelper` alone does not select Desktop's inference provider.

### Credential helper

Desktop spawns the absolute **`gh` executable** with the separate argument array above. Its single-line token output is accepted directly; no inference wrapper is needed. The supplied configuration uses a 60-second helper timeout and a 3,600-second credential cache TTL. Long-lived refresh behavior has not been validated.

The token is not inserted into rendered JSON. The installer only checks that the helper command succeeds; Desktop obtains its own runtime credential when needed. The launcher removes inherited `ANTHROPIC_*` and `CLAUDE_CODE_USE_*` overrides so the configured provider is used.

### Static model list

Both `GET /v1/models` and `GET /v1/models?limit=1000` return **404** at this gateway. Its catalog is available at authenticated `GET /models`, but that is not Desktop's discovery path. The template therefore sets **`modelDiscoveryEnabled: false`** and lists:

| Model ID | Picker display observed |
| --- | --- |
| `claude-opus-5.5` | claude-opus-5.5 |
| `claude-sonnet-5.5` | claude-sonnet-5.5 |
| `claude-haiku-5.5` | claude-haiku-5.5 |
| `claude-sonnet-5` | Sonnet 5 |
| `claude-haiku-4.5` | claude-haiku-4.5 |

All five IDs were verified in the catalog and returned HTTP 200 in direct Messages API checks. The first entry is the default. Catalog availability and account access can change; update the template deliberately rather than enabling the unsupported discovery route.

### GitHub MCP headers helper

The managed HTTP server named **github** points to `https://api.githubcopilot.com/mcp/readonly`. Its static headers contain `X-MCP-Toolsets: web_search`. Desktop runs the absolute path to `bin/ghcp-mcp-headers`, passing the absolute `gh` path through `headersHelperArgs`.

The helper prints exactly one JSON object with an **Authorization bearer header**. It fails with a fixed diagnostic and nonzero exit when credentials cannot be obtained, without printing the failed credential output. Desktop accepted this local configLibrary server as a managed source and connected with `auth: 'headers-helper'`. A direct `web_search` call succeeded; a tool call initiated from a Desktop conversation is still untested.

### Config library and isolation

Installation writes:

```text
<profile>/configLibrary/_meta.json
<profile>/configLibrary/<uuid>.json
```

The UUID file contains the rendered flat configuration, using native JSON booleans and arrays. Metadata selects it with this shape:

```json
{
  "appliedId": "<uuid>",
  "entries": [{"id": "<uuid>", "name": "GitHub Copilot"}]
}
```

The separate user-data directory allows another Desktop instance to run alongside the normal one. Ending its name in `-3p` avoids an additional third-party suffix. `disableDeepLinkRegistration: true` avoids re-registering external deep links. Embedded CLI and VM storage were observed under the isolated profile, but this launch option is not a documented guarantee of complete process or account isolation.

### Inspiration: the Claude Code CLI configuration

This setup adapts the **Claude Code CLI** configuration shown below: use GitHub CLI for credentials, Copilot as the Anthropic-compatible endpoint, and GitHub MCP for web search. Desktop needs its own helper argument arrays and configLibrary settings.

The reference CLI inference settings are:

```json
{
  "apiKeyHelper": "gh auth token --hostname github.com",
  "env": {"ANTHROPIC_BASE_URL": "https://api.githubcopilot.com"}
}
```

Its MCP entry uses CLI's `type` field and a shell-command `headersHelper`. With this checkout's JSON helper, the equivalent shape is:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/readonly",
      "headers": {"X-MCP-Toolsets": "web_search"},
      "headersHelper": "'/absolute/path/to/checkout/bin/ghcp-mcp-headers' '/absolute/path/to/gh'"
    }
  }
}
```

These snippets explain the reference; the setup scripts do not install them into your CLI configuration. Desktop instead uses `managedMcpServers`, `transport: "http"`, an executable helper path, and separate arguments.

## Applying to your real Claude Desktop (manual, at your own risk)

Quit Claude and back up **only** `~/Library/Application Support/Claude-3p/configLibrary/` before changing it. For the UI route, reopen Claude and use **Developer → Configure Third-Party Inference** with the values above. **Help → Troubleshooting → Enable Developer Mode** exposes the Developer menu when hidden. These menu paths follow [Anthropic's Desktop configuration documentation](https://claude.com/docs/third-party/claude-desktop/configuration); they were not separately verified in this setup's UI test.

For the manual-file route, keep Claude closed throughout. Copy **only the new `<uuid>.json` file** from `$HOME/claude-ghcp-test/Isolated-3p/configLibrary/` into the real configLibrary folder, creating that folder if it did not exist. Choose a UUID that is not already present; do not overwrite an existing configuration file. **Never copy the isolated `_meta.json` over the real one.** The selector must be merged: preserve all existing entries and other metadata fields, append `{ "id": "<uuid>", "name": "GitHub Copilot" }`, and set `appliedId` to the new ID. If `_meta.json` does not exist, create it with that entry and selector.

After backing up the folder and copying the new UUID file, set `CONFIG_ID` to that file's name without `.json`. The following Python one-liner validates the UUID and existing entries, refuses duplicate IDs and symlinked metadata, and writes the merged JSON through a private temporary file before atomic replacement. It does not replace the existing entry list. Keep Claude closed and do not run concurrent configuration editors while using it; this is a manual operation, not a live-profile transaction.

```sh
CONFIG_ID='REPLACE_WITH_THE_NEW_UUID'
python3 -c 'import json, os, pathlib, sys, tempfile, uuid; p=pathlib.Path(sys.argv[1]).expanduser(); i=sys.argv[2]; assert str(uuid.UUID(i)) == i, "Use a canonical UUID"; assert not p.is_symlink(), "Refusing symlinked metadata"; c=p.parent/(i+".json"); assert c.is_file() and not c.is_symlink(), "Copy the new UUID file first"; d=json.loads(p.read_text()) if p.exists() else {"entries":[]}; assert isinstance(d,dict) and isinstance(d.get("entries"),list) and all(isinstance(e,dict) and isinstance(e.get("id"),str) for e in d["entries"]), "Invalid existing metadata"; assert all(e["id"] != i for e in d["entries"]), "ID already exists"; d["entries"].append({"id":i,"name":"GitHub Copilot"}); d["appliedId"]=i; f=tempfile.NamedTemporaryFile(mode="w",dir=p.parent,prefix=".meta-",delete=False); json.dump(d,f,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno()); f.close(); os.replace(f.name,p)' "$HOME/Library/Application Support/Claude-3p/configLibrary/_meta.json" "$CONFIG_ID"
```

`scripts/render-config` prints the flat UUID-file contents only; it does not create a metadata selector. Existing managed configuration can take precedence over a local library. Do not copy the rest of the profile. No setup script in this repository applies or restores a real profile.

To revert, quit Claude and **replace the entire configLibrary folder with the folder you backed up**, then restart. Overlaying the backup can leave the new UUID file behind. If no folder existed before setup, remove only the newly created configLibrary folder while Claude is closed.

## Privacy and network boundaries

Rendering and configuration installation are local operations, apart from whatever GitHub CLI needs to obtain its stored credential. Helper stdout is discarded by the installer; generated config holds paths and settings, not a token. Normal inference sends prompts to GitHub Copilot, and MCP calls contact GitHub's MCP service. Direct validation requests also use provider quota.

The tested Desktop build refreshed a **hosted model catalog** even with provider model discovery disabled. Its exact destination and payload were not captured; it may contact Anthropic or other non-GHCP services. Desktop also downloads runtime components. This configuration demonstrates GHCP inference routing, not exclusively GHCP traffic.

Application logs were observed in **`~/Library/Logs/Claude/`**, shared with the normal instance. Launcher stdout/stderr is captured separately under `<profile>/logs/`. OS state such as Keychain items may also be shared. The lifecycle checksum comparison concerns one configuration file, not every file in either normal profile.

Live-check output masks recognized credential patterns, but do not treat it as a complete privacy scrub. Shared-log excerpts are filtered by time and terms, not generally by process identity; correlate them with the isolated session before sharing. Keep raw profiles, screenshots, paths and account details out of public commits.

## Undo and uninstall

Inspect the stop selection first, replacing the PID placeholder:

```text
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <PID of your normal Claude> --dry-run
scripts/stop-isolated "$HOME/claude-ghcp-test/Isolated-3p" --protect-pid <PID of your normal Claude>
```

The stop command rechecks the exact isolated `--user-data-dir` match immediately before SIGTERM and verifies the protected instance afterward. It does not issue a broad application-name kill or force termination. Once the isolated app has stopped, delete its profile folder if you want to discard its data, then remove the checkout if no other configuration references its helper. Removing local files does not revoke your GitHub sign-in.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Installation cannot obtain credentials | Sign in with GitHub CLI and select the active account; check environment-token overrides. Never paste a token into the configuration. |
| Helper runs in Terminal but fails in Desktop | Verify the absolute paths, executable permissions, GUI availability of Python, and that the checkout is outside protected/cloud folders. |
| Empty model picker | Confirm the selected library entry has all five full IDs and `modelDiscoveryEnabled: false`; a 404 discovery endpoint cannot populate the list. |
| 401/403 on inference | Check the active account's Copilot access and bearer authentication; token retrieval alone does not establish entitlement. |
| 404 on messages | Use the root gateway base URL without `/v1`; the request endpoint must be `/v1/messages`. |
| Model-specific 400 | Check request features such as reasoning effort; earlier Haiku 4.5 CLI probes rejected an unsupported effort field. |
| MCP connection fails | Check `transport: "http"`, the read-only URL, helper arguments and static toolset header. Desktop logs should show the helper and connection outcome. |
| Launcher refuses the protected PID | Select the currently running normal main process, not a Helper or an old PID; do not bypass the guard. |
| Configuration changes do not appear | Check the metadata selector, restart only the isolated instance, and account for managed settings that override local configuration. |

## Known limitations

**Auto mode:** `inferenceGatewayAutoModeServerChecks` is false. Desktop uses its built-in check instead of relying on the provider-side review. Acceptance of the new beta header alone does not validate `safeguards` or `safeguard_results` compatibility.

**Coverage:** the five models passed direct inference checks, but only Opus 5.5 was exercised in a real Desktop conversation. Desktop-initiated web search, long sessions, token refresh, context limits, and separate Code and Cowork tab workflows remain untested. Hosted-catalog traffic and shared logs prevent treating the isolated instance as a complete network or storage boundary.

## References

- [Desktop gateway configuration](https://claude.com/docs/third-party/claude-desktop/gateway)
- [Desktop configuration reference](https://claude.com/docs/third-party/claude-desktop/configuration)
- [Desktop credential helpers](https://claude.com/docs/third-party/claude-desktop/credential-helper)
- [GitHub CLI authentication](https://cli.github.com/manual/gh_auth)
