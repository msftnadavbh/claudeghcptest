# Validation record

Live observations were collected on macOS with Claude Desktop **6.28899.6** and embedded Claude Code **2.1.330**. Results below distinguish Desktop UI checks, direct API probes, and offline tests. No local profile, account identifier, process ID, or raw diagnostic capture is included.

## Live checks

| Check | Result | Evidence scope |
| --- | --- | --- |
| Isolated Desktop alongside normal app | Passed | A separate profile ending in `-3p` ran alongside the normal app; protected main-process identity/start time and one specified config checksum were compared. This is not a full profile inventory. |
| Gateway activation and runtime credential | Passed | Desktop logged third-party Gateway mode, the GitHub Copilot inference host, and successful use of the absolute `gh` helper. |
| Model picker | Passed | Five configured `inferenceModels` entries appeared in the isolated window. |
| Desktop conversation | Passed | An Opus 5.5 turn completed in the isolated window. |
| Five-model direct inference | Passed | All configured model IDs returned HTTP 200 from `/v1/messages`; this is not a Desktop conversation test for every model. |
| GitHub MCP connection | Passed | Desktop connected to managed server `github` with `auth: 'headers-helper'`. |
| Direct MCP `web_search` | Passed | Direct `tools/call` returned HTTP 200 with search results. |
| Desktop-conversation-initiated web search | Not observed | The connection and direct tool result do not establish that Desktop invoked the tool from a conversation. |
| Runtime token absent from checked storage | Passed within checked scope | No token was found in repository files or installed configLibrary JSON. This was not a scan of all application files or logs. |
| Default-mode install/uninstall sandbox | Passed | A temporary HOME with a pre-existing foreign entry preserved foreign metadata, created a private backup, and restored the previous selector and library inventory on removal. |
| Default-mode sandbox startup | Partially observed | Across sandbox startup observations, a base `--user-data-dir` without `-3p` activated the third-party library; one run also recorded the Copilot host and GitHub MCP connection, while another recorded gateway activation only before shutdown. |
| Default-mode sandbox picker | Not observed | The fresh sandbox profile stayed on the welcome screen without UI input. The identical model list produced a picker in isolated-mode validation. |

Observed Desktop diagnostics included:

```text
[custom-3p] 3P mode active { provider: 'gateway' }
[custom-3p] inference apiHost=https://api.githubcopilot.com/
[custom-3p] Model discovery: off (modelDiscoveryEnabled=false); picker = 5 (inferenceModels)
[custom3p-mcp] connected { name: 'github', toolCount: 1, auth: 'headers-helper' }
```

The isolated conversation requested a short fixed phrase and received it from `claude-opus-5.5`; the UI completed and the application log recorded turn success. A separate sandbox welcome-screen run sent no UI input. Desktop also refreshed a hosted model catalog. These results do not prove full network or storage isolation.

## Claude Code tab

The Desktop Code tab was opened with Manual permissions and a local fixture. Its Code child had `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, and `ANTHROPIC_DEFAULT_HAIKU_MODEL` set to the corresponding dotted 5.5 IDs supplied by `anthropicFamilyTier` and `isFamilyDefault` metadata.

| Command | Desktop observation | Qualification |
| --- | --- | --- |
| Prompt and Cmd+; side chat (`/btw`) | Passed | Side chat recalled context from the main conversation. The literal `/btw` text submission was not separately exercised. |
| `/insights` | Command ran | Desktop generated three analyses, but all sessions were classified `warmup_minimal`; the report included 0 of 4 sessions. Substantive eligible sessions produced a populated report in a separate SDK test, not the Desktop UI. |
| `/model` | Passed | Switched to Haiku 5.5 and Sonnet 5.5; each returned a reply. |
| `/context`, `/compact` | Passed | Context displayed a category breakdown; compaction reported tokens saved. |
| `/mcp`, `/status` | Passed | MCP showed `github` as Web, Managed, Connected; status reflected the connection and managed settings. |
| `/cost` | Passed | Opened local Usage settings, which omit provider-specific currency costs. |
| `/effort`, `/config`, `/permissions`, `/memory`, `/resume` | Passed for observed action | Effort accepted a session override; other commands opened their corresponding local settings/list/dialog. No settings were changed and no session was resumed. |
| `/usage` | SDK-only | Passed in SDK testing; not established as a Desktop command. |
| `/hooks` | Terminal-only | Desktop directs users to Claude Code in a terminal. |
| `/agents` | Removed | The tested embedded version displayed a removal notice for the old wizard. |
| Account/cloud-only commands | Unavailable | These require first-party identity or Anthropic-hosted cloud features. |

In a headless SDK test against the same embedded engine, three substantive local sessions produced a populated `/insights` report. The engine's eligibility filters can exclude short or warmup sessions. That result is separate from the Desktop UI observation above.

Auto-mode server checks are set to `false` in the configuration. When enabled in a probe, GitHub Copilot rejected the `safeguards` field with HTTP 400. Opus requests received intermittent HTTP 429 responses during report generation; a later retry succeeded without configuration changes.

## Direct API and MCP results

| Request | Result |
| --- | --- |
| Authenticated `GET /models` | HTTP 200; configured Claude IDs present for the tested account. |
| `GET /v1/models` and `GET /v1/models?limit=1000` | HTTP 404. |
| `POST /v1/messages` for each of five configured models | HTTP 200. |
| Streaming Messages request | HTTP 200 with server-sent events. |
| `POST /v1/messages/count_tokens` | HTTP 200. |
| GitHub MCP `initialize` and `tools/list` | HTTP 200; `web_search` available. |
| GitHub MCP `tools/call` for `web_search` | HTTP 200 with web results. |

Configured model IDs: `claude-opus-5.5`, `claude-sonnet-5.5`, `claude-haiku-5.5`, `claude-sonnet-5`, and `claude-haiku-4.5`. Results apply to the tested account and request shapes; available models and accepted request features can change.

## Offline test suite

From the repository root, run:

```sh
python3 -B -m unittest discover -s tests -v
```

The 36 tests cover config rendering and model-family defaults; model-list upgrades; helper paths and MCP output; default-target resolution and process detection; MDM refusal; backup, metadata merge, idempotency, and uninstall selection behavior; dry-run and symlink refusal; state/provenance validation; snapshot checks; isolated-mode compatibility and exact process selection; token-pattern checks; auth preflight; private writes and failure cleanup; interrupted install/removal recovery and synchronization order; and test-only HOME and Desktop/Code I/O guards.

Tests use a temporary HOME for home-relative operations, a fake `gh`, sanitized subprocess environments, mocked process lists/signals, and no network. The test-only Python audit guard checks protected profile paths in the main test process and Python children. It is not an OS sandbox and does not contain arbitrary native or shell children. Fault injection validates cleanup, retry behavior, and synchronization call order; it does not simulate power loss or guarantee hardware durability.

GitHub Actions runs the offline tests on `macos-latest` and `ubuntu-latest`. A publication-safety step scans tracked files for personal paths and credential patterns. The Copilot coding agent setup workflow installs Python 3.12 on Ubuntu and is triggered manually or when its workflow file changes in a pull request. Repository instructions for contributors are in [`.github/copilot-instructions.md`](../.github/copilot-instructions.md).

## Test-only sandbox validation

Default-mode sandbox install, launch, and uninstall are validation procedures, not customer setup. Never run `./install` or `./uninstall` against a real HOME for validation, and never launch Desktop as part of the offline test suite. For permitted manual checks, use a fresh temporary HOME outside the account's Library, set `GHCP_TEST_FORBID_REAL_HOME=1`, and invoke the entry point with `--sandbox-home`. Supply a fake `gh` for dry-run/authentication checks, for example:

```sh
HOME="/path/to/fresh-temp-home" GHCP_TEST_FORBID_REAL_HOME=1 \
  ./install --dry-run --sandbox-home --gh /path/to/fake-gh
```

`--sandbox-home` rejects the account HOME and paths inside its Library. It treats unqualified Desktop launches as the OS account's app and still refuses an explicit launch targeting either sandbox config profile. `GHCP_TEST_FORBID_REAL_HOME` is a test-only guard against real account configuration locations, including resolved aliases. A temporary sandbox can be a separate directory under the account home if outside its Library.

`GHCP_TEST_HOME` is strictly test-only. It is honored only when it exactly matches `HOME` and `GHCP_TEST_FORBID_REAL_HOME=1` is also set; by itself it cannot redirect a customer invocation. The Python `sitecustomize.py` guard used by tests audits file access in the main process and Python subprocesses and requires subprocesses to retain the fixture HOME. These environment variables do not provide an OS-level security boundary.

The recorded sandbox startup used a substituted HOME and could not read the normal OS credential store, so its live validation supplied a credential in memory through `GH_TOKEN`; the token was not saved to configuration or evidence. That is a detail of the recorded validation setup, not a recommended customer sign-in method. The tested normal profile's log location was `~/Library/Logs/Claude-3p/main.log`.

## Known validation limits

The normal account's full profile was not compared; the process/checksum comparison covers only the main process identity/start time and one specified configuration file. A fresh sandbox profile stayed on its welcome screen, so no model picker was observed in the default-mode sandbox run. Across default-mode sandbox startup observations, one run recorded gateway activation, the inference host, and MCP connection; another recorded gateway activation only before shutdown. Desktop-conversation-initiated web search and a populated Desktop Code `/insights` report have not been observed. Long sessions, credential refresh after expiry, large-context behavior, Cowork, and Auto-mode safeguards compatibility remain unverified. Hosted model catalog traffic is observed, so the app is not limited to GitHub Copilot endpoints. See the [guide](guide.md#privacy-logs-and-known-limitations) for customer-facing impact and limitations.
