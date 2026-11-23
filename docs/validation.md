# Validation record

The configuration was live-tested on **macOS with Claude Desktop 6.28899.6** and embedded Claude Code **2.1.330**. This record summarizes results without publishing local profiles, account details, machine paths, process IDs, or raw diagnostic captures.

## Results

| Check | Result | What establishes it |
| --- | --- | --- |
| Separate Desktop instance | Passed | An isolated `--user-data-dir` ending in `-3p` ran alongside the normal app. The protected main PID/start time and one specified configuration-file checksum stayed unchanged. |
| GHCP gateway mode | Passed | Desktop reported third-party gateway mode and the Copilot inference host. |
| Runtime inference credential | Passed | Desktop ran the absolute `gh` executable with `auth token --hostname github.com` and reported helper success. |
| Model picker | Passed | Desktop reported five entries from `inferenceModels`; all five appeared in the isolated window. |
| Desktop conversation | Passed | A real Opus 5.5 turn completed with the requested short response in the isolated window; Desktop logged turn success. |
| Five-model direct inference | Passed | Each configured model ID returned HTTP 200 from `/v1/messages`. This does not establish a Desktop conversation with each model. |
| GitHub MCP connection | Passed | Desktop connected with `auth: 'headers-helper'` and one available tool. |
| Direct MCP web search | Passed | A direct `web_search` call using the same helper/static headers returned HTTP 200 and search results. |
| Desktop-initiated web search | Not yet observed | Connection and direct-tool evidence do not prove tool invocation from a Desktop conversation. |
| Credential storage | Passed within checked scope | No runtime token was found in repository files or installed configLibrary JSON. This was not a scan of every application file or log. |
| Offline regression suite | Passed | **36 tests** pass, including upgrading a managed string-only model list to tier objects under the same UUID. |
| Default-mode sandbox installation | Passed | HOME-scoped default target; private backup; foreign metadata preserved; uninstall restored the original selector and library inventory. |
| Default-mode sandbox startup | Passed | A base `--user-data-dir` without `-3p` activated the sibling third-party library, GHCP inference host and GitHub headers-helper MCP connection. |
| Default-mode sandbox picker log | Not observed | The fresh profile stayed on its welcome screen without UI input; identical `inferenceModels` configuration produced `picker = 5` in the isolated-mode validation. |

The protected-app comparison is deliberately narrow: it covers the normal main process identity/start time and `~/Library/Application Support/Claude-3p/claude_desktop_config.json` when present. It does not prove unchanged contents across either entire normal profile.

## Desktop observations

The following log excerpts describe the isolated run without local identifiers:

```text
[custom-3p] 3P mode active { provider: 'gateway' }
[custom-3p] inference apiHost=https://api.githubcopilot.com/
[custom-3p] Model discovery: off (modelDiscoveryEnabled=false); picker = 5 (inferenceModels)
[custom3p-mcp] connected { name: 'github', toolCount: 1, auth: 'headers-helper' }
```

The test conversation asked for **“GHCP Desktop isolated chat OK.”** and received that response from `claude-opus-5.5`. The UI showed that the response finished, and the application log reported that the turn succeeded. The picker listed the five configured IDs, formatting `claude-sonnet-5` as **Sonnet 5**.

The isolated run used shared `~/Library/Logs/Claude/` logs; the default-mode sandbox launch used `~/Library/Logs/Claude-3p/`. Desktop also reported a hosted model-catalog refresh. Neither observation should be interpreted as full storage or network isolation.

## Claude Code tab commands

The isolated Desktop opened **Code** with Manual permissions and a local Git fixture. Its own Code child had all three `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` values set to the corresponding dotted 5.5 IDs. The following checks used that Desktop window:

| Command | Desktop status | What was observed |
| --- | --- | --- |
| Normal prompt; `/btw` side chat | PASS | Opus answered “Indigo clock.” **Cmd+;** opened a side chat that correctly recalled those words without the question repeating them. Literal `/btw` submission was not separately exercised. |
| `/insights` | Works (Desktop gateway analysis; populated headless report) | Desktop wrote three model-generated analyses of session goals and outcomes under `usage-data/facets/`. All were classified as `warmup_minimal`, so the final HTML correctly included **0 of 4 sessions**. With substantive sessions, the same engine produced the populated report described below. |
| `/model` | PASS | Switched to Haiku 5.5, then Sonnet 5.5, and received a reply after each switch. Both model identities appeared in the corresponding assistant transcript records. |
| `/context`, `/compact` | PASS | Context showed a category breakdown for a 1M window; compaction reported 84.8K tokens saved. |
| `/mcp`, `/status` | PASS | MCP listed `github` as Web, Managed, Connected; status showed the connection and managed settings in effect. |
| `/cost` | PASS | Resolved to Usage settings, which explicitly omits provider-specific currency costs. |
| `/effort low`, `/config`, `/permissions`, `/memory`, `/resume` | PASS for observed action | Effort confirmed the session override. The others opened Code settings, settings with permission controls, the Memory file list and the resume dialog, respectively. No settings were edited or session restored from the dialog. |
| `/hooks` | Terminal only | Desktop directed the user to Claude Code in a terminal. |
| `/agents` | Wizard removed in this build | Desktop displayed the removal notice. Neither this nor the `/hooks` restriction is a Copilot gateway failure. |
| `/help` | Inconclusive | Focus left the test app after submission; destination not inspected. |
| `/clear`, `/init`, `/review`, `/export`, `/todos`, remaining menu entries | Not tested in Desktop | Foreground testing stopped when another app took focus. Separate engine results follow. |

**Engine comparison.** A separate controlled test used the same **2.1.330** engine against Copilot, with and without the three tier pins. An SDK result is not a Desktop GUI result. For comparison, the terminal tests used an interactive TUI.

| Command | Status | Notes |
| --- | --- | --- |
| `/btw` | PASS (TUI); unavailable as SDK text | The terminal overlay and an SDK fork answered using the parent conversation. Literal SDK `/btw` was rejected before inference. |
| `/insights` | PASS (SDK) | Three eligible local sessions produced a populated report: six user messages, twelve Opus requests, all HTTP 200. Also passed without pins. |
| `/model` | PASS (SDK) | Each of the five exact IDs accepted a switch and subsequent prompt. An Opus validation retried successfully after throttling. |
| `/compact`, `/context`, `/clear` | PASS (SDK) | Compaction produced a persisted summary, context reported model-specific limits, and clear reset the conversation. |
| `/effort`, `/config` | PASS (SDK text) | Low effort accepted for the session; `/config` returned its `key=value` interface. |
| `/mcp` | PASS (SDK command) | Reported no servers in the headless fixture; this does not test Desktop's managed GitHub connection. |
| `/cost`, `/usage` | PASS (SDK) | Local estimated cost; no Copilot subscription balance. |
| `/init`, `/review` | PASS for fixture creation and bug identification (SDK) | Init created `CLAUDE.md`; review identified a seeded subtraction bug via file reads. The lab sandbox blocked the Git diff. |
| `/agents` | Removal notice (SDK) | The old wizard is no longer present. |
| `/status`, `/hooks`, `/permissions`, `/memory`, `/resume`, `/export`, `/help` | PASS opening TUI panels; unavailable as SDK text | Each returned a local unavailability message in print mode, without an inference request. |
| `/todos` | Unavailable | Unknown in the terminal; SDK sent the text to the model instead of dispatching a command. |
| `/remote-control`, `/voice`, `/upgrade`, `/usage-credits` | N/A | Require first-party identity or subscription services; a GHCP bearer does not supply them. |
| Cloud sessions, `/schedule`, `/__remote-workflow`, Design consent | N/A | Require Anthropic-hosted services, remote execution, or Design authorization. Local `/loop` is distinct: it created an in-session schedule in the SDK lab. |

In the headless lab with all three tier pins set, the session title request went to Haiku, and WebFetch made requests to both Haiku and Opus (cmdlab `REPORT.md`, “Session title” and “WebFetch” rows). The runs did not isolate the effect of individual pins.

Neither the successful side question nor the populated report required a new credential setting or Auto mode classifier override. With server-side Auto mode checks enabled, Copilot rejected the `safeguards` field (HTTP 400); the config retains `inferenceGatewayAutoModeServerChecks: false`. The lab also observed intermittent HTTP 429s on Opus during report generation. A later retry succeeded without changing the model configuration. See [gateway limitations](https://code.claude.com/docs/en/llm-gateway-connect) and [local report eligibility](https://code.claude.com/docs/en/costs#analyze-your-usage-patterns).

## Direct API and MCP checks

| Request | Observed result |
| --- | --- |
| Authenticated `GET /models` | HTTP 200; all five configured Claude IDs present |
| `GET /v1/models` | HTTP 404 |
| `GET /v1/models?limit=1000` | HTTP 404 |
| `POST /v1/messages` for each configured model | HTTP 200 |
| Streaming Messages request | HTTP 200 with SSE response events |
| `POST /v1/messages/count_tokens` | HTTP 200 |
| GitHub MCP `initialize` and `tools/list` | HTTP 200; `web_search` available |
| GitHub MCP `tools/call` for `web_search` | HTTP 200 with web results |

The directly tested model IDs were `claude-opus-5.5`, `claude-sonnet-5.5`, `claude-haiku-5.5`, `claude-sonnet-5`, and `claude-haiku-4.5`. These results apply to the tested account and request shapes; availability and accepted request features can change.

## Run the offline suite

From the checkout:

```sh
python3 -B -m unittest discover -s tests -v
```

The **36 tests** cover rendered JSON and model-family defaults, upgrade of a managed model list, absolute helper paths, MCP output/error handling, default target resolution, alternate/renamed main-app paths, Helper-only and isolated process rows, ambiguous profile arguments, MDM refusal, private backups, metadata merge and idempotency, uninstall with foreign entries/fields and later selections, deleted previous targets, absent libraries/selectors, dry-run, symlinks, per-publication snapshot checks, isolated compatibility, exact stop selection, token-pattern scanning, credential preflight, private JSON writes, complete state/provenance validation, failure cleanup, staged backup failures, interrupted install/removal recovery, fsync ordering, test-only HOME gating, and Desktop/Code I/O tripwires.

Each test sets a temporary HOME before home-relative operations. Subprocesses receive explicit sanitized environments without inherited credential/configuration overrides. A fake `gh` handles authentication-related tests. The test-only Python audit tripwire rejects real Claude profile I/O and real `~/.claude` / `~/.claude.json` access in the main test process and Python children, for lexical paths and resolved aliases; rejection is tested without opening protected files. This is not an OS sandbox and does not contain arbitrary native/shell children. Stop tests mock signaling rather than operating on running apps. Fault injection verifies recoverability and synchronization call order, not power-loss or hardware durability.

## Default-mode sandbox validation

Default install and uninstall were exercised with a dedicated sandbox HOME, never the account's actual HOME. A fake foreign library entry, its selected ID and a custom metadata field were seeded first. The installer merged its own entry and created a `0700` timestamped library backup. After startup validation and exact-PID shutdown, uninstall restored the foreign entry, original selector, foreign file bytes and library inventory. Both pre-existing Desktop main processes retained their argv/start times and the protected configuration checksum was unchanged.

For a deliberate repeat, select a fresh sandbox outside the account's Library, set `HOME` and `CLAUDE_CONFIG_DIR` to sandbox paths, and set `GHCP_TEST_FORBID_REAL_HOME=1`. Use `./install --sandbox-home`, then launch the Desktop executable with `--user-data-dir="$HOME/Library/Application Support/Claude"` (**without** `-3p`). This exercises Desktop's real suffix derivation rather than the isolated-mode shortcut. GitHub CLI still needs credentials: in this validation an account credential was passed through `GH_TOKEN` in memory because OS credential lookup under the substituted HOME failed; it was never saved in configuration or evidence.

`--sandbox-home` requires a HOME distinct from the OS account home and outside its Library. It explicitly treats unqualified Desktop launches as belonging to the OS account rather than the caller's substituted HOME. It still refuses a process explicitly targeting the sandbox's base or `-3p` user-data path, and fails closed on ambiguous argv. Without this flag, a nonstandard HOME is rejected outside the hermetic unit-test environment. The additional test-only guard refuses real account configuration locations, including resolved aliases; a sandbox may be a separate subdirectory of the account home.

`GHCP_TEST_HOME` is a unit-test-only exception, honored only when it exactly matches HOME and `GHCP_TEST_FORBID_REAL_HOME=1` is also set. It cannot redirect an ordinary customer invocation by itself.

After the recorded launch time, **`~/Library/Logs/Claude-3p/main.log`** contained gateway activation, the Copilot inference host, and a GitHub MCP connection with `auth: 'headers-helper'`. The base-path startup changes the log destination from the already-suffixed isolated launch's `Claude/main.log`. No UI input was sent. The fresh profile remained on its welcome screen, so `picker = 5` was **not observed in this sandbox run**; the same five `inferenceModels` were verified in installed JSON and produced that picker log in the isolated-mode validation.

Stop only the sandbox main PID after re-reading its argv and verifying the exact sandbox `--user-data-dir`; use SIGTERM only. Verify protected process identities and checksum again, then run `./uninstall --sandbox-home` under the same sandbox HOME and guard. Keep masked evidence outside the repository. Do not run default installation or removal against a real account HOME as part of tests.

During the review-fix repeat, default installation/removal and foreign-library restoration passed, but the sandbox welcome screen emitted only gateway activation before shutdown; inference-host and MCP startup checks were not observed in that repeat (they passed in the earlier run above). Desktop ignored SIGTERM while on the welcome screen. The supervisor verified and force-stopped only the sandbox main PID, after which removal ran successfully and protected process/checksum checks passed. The local validation harness now allows a supervisor-authorized sandbox-only SIGKILL fallback after 20 seconds, re-verifying the exact main-process argv immediately before signaling. The shipped isolated lifecycle helper continues to use SIGTERM only.

## Repeat live checks deliberately

Live validation needs macOS, a signed-in GitHub CLI account with inference access, and a separately installed profile. Follow [setup](guide.md#setup) first. Every `scripts/live-check.py` action requires `--profile <isolated-profile>`, `--evidence <local-evidence-directory>`, and `--protect-pid <PID of your normal Claude>`.

| Action | Purpose |
| --- | --- |
| `baseline --name before` | Record the protected process/checksum and isolated process selection before launch |
| `probe` | Check catalog/discovery endpoints, a Sonnet 5.5 Messages request, streaming, token counts, and MCP initialization/tool listing |
| `web-search` | Make one direct MCP web-search request |
| `capture --name final` | Save masked relevant log excerpts, installed configuration and lifecycle observations; expects the earlier `before.json` |
| `audit` | Search repository and installed configLibrary JSON for the exact runtime token, reporting only results/paths |
| `record --name result -- <command>` | Save masked command output |

The current `probe` action does not loop over all five models; the five-model result above also includes separate direct checks. A probe does not send a Desktop chat. Verify that any interactive window belongs to the isolated process before sending input, and confirm Desktop response/model-picker behavior separately.

Live requests consume provider usage. Evidence may include personal paths or conversations despite credential masking. Keep it local and review any excerpt before sharing, especially because the application log is shared and automatic filtering is not generally process-scoped.

## Not yet validated

**Provider-side Auto mode safeguards**, long-running sessions, credential refresh after expiry, large-context behavior and **Cowork** remain unverified. The supplied configuration disables provider-side Auto mode checks; a beta-header-only request succeeded but does not prove the full safeguards protocol. A Desktop-initiated MCP web-search call and a populated Desktop Code `/insights` report have not yet been observed.

No installation into a real account's normal profile was performed during validation. Default installation and removal are implemented and covered through the sandbox target described above; customer usage is documented in the [guide](guide.md#setup).
