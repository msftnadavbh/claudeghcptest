#!/usr/bin/env python3
"""Opt-in live probes and masked evidence collection; never stores credentials."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from desktop import ROOT, isolated_path, render, protected_snapshot, matching_pids


def mask(text):
    text = re.sub(r"gh[pousr]_[A-Za-z0-9_]+|github" + r"_pat_[A-Za-z0-9_]+|sk" + r"-ant[A-Za-z0-9_-]+", "[REDACTED]", text)
    return re.sub(r"(?i)(Bearer\s+)[^\s\"'\\,}]+", r"\1[REDACTED]", text)


def save(directory, name, value):
    directory.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, indent=2)
    (directory / name).write_text(mask(text) + "\n")


def request(path, token, body=None, extra=None):
    headers = {"Authorization": "Bearer " + token, "anthropic-version": "2023-06-01"}
    headers.update(extra or {})
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("https://api.githubcopilot.com" + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        content = response.read().decode()
        return {"path": path, "status": response.status, "body": mask(content)}


def probes(directory):
    config = render()
    helper = subprocess.run([config["inferenceCredentialHelper"], *config["inferenceCredentialHelperArgs"]],
                            text=True, capture_output=True, check=True)
    token = helper.stdout.strip()
    assert token and not any(c.isspace() for c in token)
    models = request("/models", token)
    catalog = json.loads(models["body"])
    available = [row["id"] for row in catalog.get("data", []) if row.get("vendor") == "Anthropic"]
    configured = [m["name"] if isinstance(m, dict) else m for m in config["inferenceModels"]]
    save(directory, "catalog.json", {"status": models["status"], "claude_models": available,
                                     "configured_models_present": all(m in available for m in configured)})
    results = []
    for path in ("/v1/models", "/v1/models?limit=1000"):
        results.append(request(path, token))
    body = {"model": "claude-sonnet-5.5", "max_tokens": 64,
            "messages": [{"role": "user", "content": "Reply with exactly: GHCP direct probe OK"}]}
    results.append(request("/v1/messages", token, body))
    results.append(request("/v1/messages/count_tokens", token,
                           {"model": body["model"], "messages": body["messages"]}))
    results.append(request("/v1/messages", token, dict(body, stream=True),
                           {"anthropic-beta": "dangerous-tool-use-2026-09-03"}))
    save(directory, "api-probes.json", results)
    server = config["managedMcpServers"][0]
    result = subprocess.run([server["headersHelper"], *server["headersHelperArgs"]],
                            text=True, capture_output=True, check=True)
    headers = json.loads(result.stdout)
    assert headers == {"Authorization": "Bearer " + token}
    mcp_headers = dict(server["headers"], Accept="application/json, text/event-stream")
    mcp = []
    for body in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "ghcp-desktop-probe", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}):
        mcp.append(request("/mcp/readonly", headers["Authorization"][7:], body, mcp_headers))
    save(directory, "mcp-probes.json", {"helper": "one JSON object, Authorization Bearer [REDACTED], exit 0", "requests": mcp})
    print("Saved masked API/catalog/MCP probe evidence")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["baseline", "capture", "probe", "record", "web-search", "audit"])
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--protect-pid", type=int, required=True)
    parser.add_argument("--name", default="snapshot")
    args, command = parser.parse_known_args()
    if command and args.action != "record":
        parser.error("unexpected arguments: " + " ".join(command))
    profile = isolated_path(args.profile)
    if args.action in ("baseline", "capture"):
        state = {"time": datetime.datetime.now().isoformat(), "protected": protected_snapshot(args.protect_pid),
                 "protected_pid": args.protect_pid, "isolated_pids": matching_pids(profile), "profile": str(profile)}
        save(args.evidence, args.name + ".json", state)
        if args.action == "capture":
            for path in (profile / "logs").glob("*.log"):
                save(args.evidence, args.name + "-" + path.name, path.read_text(errors="replace"))
            # App logs are shared on this Desktop build. Keep only relevant 3P
            # records from this run, not unrelated first-party chat/account logs.
            baseline = json.loads((args.evidence / "before.json").read_text())["time"][:19].replace("T", " ")
            source = Path.home() / "Library/Logs/Claude/main.log"
            lines = source.read_text(errors="replace").splitlines()
            excerpt = [line for line in lines if line[:19] >= baseline and
                       any(term in line for term in ("[custom-3p]", "[custom3p-mcp", str(profile), "[Result]"))]
            save(args.evidence, "desktop-main-excerpts.log", "\n".join(excerpt))
            meta = json.loads((profile / "configLibrary/_meta.json").read_text())
            save(args.evidence, "installed-config.json", json.loads((profile / "configLibrary" / (meta["appliedId"] + ".json")).read_text()))
        print(json.dumps(state, indent=2))
    elif args.action == "probe":
        probes(args.evidence)
    elif args.action == "web-search":
        server = render()["managedMcpServers"][0]
        headers = json.loads(subprocess.check_output([server["headersHelper"], *server["headersHelperArgs"]], text=True))
        result = request("/mcp/readonly", headers["Authorization"][7:], {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "web_search", "arguments": {"query": "What is the official GitHub CLI website?"}}},
            dict(server["headers"], Accept="application/json, text/event-stream"))
        save(args.evidence, "web-search-probe.json", result)
        print("Saved masked web_search tool-call response, HTTP " + str(result["status"]))
    elif args.action == "audit":
        config = render()
        token = subprocess.check_output([config["inferenceCredentialHelper"], *config["inferenceCredentialHelperArgs"]]).strip()
        files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
        paths = [ROOT / name for name in files] + list((profile / "configLibrary").glob("*.json"))
        contaminated = [str(path) for path in paths if token in path.read_bytes()]
        save(args.evidence, "token-audit.json", {"files_checked": len(paths), "token_persisted": bool(contaminated), "offending_paths": contaminated})
        print("Exact runtime-token audit: " + ("FAIL" if contaminated else "PASS"))
        sys.exit(bool(contaminated))
    else:
        command = command[1:] if command[:1] == ["--"] else command
        result = subprocess.run(command, capture_output=True, text=True)
        save(args.evidence, args.name + ".txt", result.stdout + result.stderr)
        try:
            payload = json.loads(result.stdout).get("result", {})
            shot = payload.get("screenshot")
            snapshot = payload.get("snapshot", {})
            if shot and snapshot.get("app", {}).get("pid") in matching_pids(profile):
                shutil.copyfile(shot["path"], args.evidence / (args.name + ".png"))
        except (ValueError, KeyError):
            pass
        print(mask(result.stdout + result.stderr))
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
