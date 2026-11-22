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
| Offline regression suite | Passed | **11 tests** pass with temporary HOME fixtures and synthetic credentials. |

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

Application logs were found in the shared `~/Library/Logs/Claude/` directory. Desktop also reported a hosted model-catalog refresh. Neither observation should be interpreted as full storage or network isolation.

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

The **11 tests** cover rendered JSON and required settings, absolute executable paths, MCP output/error handling, metadata preservation, forbidden-profile and symlink refusal, exact stop-process selection including Helper/GPU rows, token-pattern scanning, discarded-output credential preflight, required protected-PID arguments, private JSON-file creation, and the test I/O guard.

Each test sets a temporary HOME before home-relative operations. Subprocesses receive explicit sanitized environments without inherited credential/configuration overrides. A fake `gh` handles authentication-related tests. The test-only Python audit guard rejects real Claude profile I/O in the main test process and Python children; its rejection is tested without opening the protected files. Stop tests mock signaling rather than operating on running apps.

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

**Provider-side Auto mode safeguards**, long-running sessions, credential refresh after expiry, large-context behavior, and separate **Code** and **Cowork** tab workflows remain untested. The supplied configuration disables provider-side Auto mode checks; a beta-header-only request succeeded but does not prove the full safeguards protocol. A Desktop-initiated MCP web-search call has not yet been observed.

No installation into the normal profile was performed. Manual application/reversion guidance is documented in the [guide](guide.md#applying-to-your-real-claude-desktop-manual-at-your-own-risk), not implemented by setup scripts.
