"""Small, dependency-free configuration and isolated-process utilities (macOS)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
APP = Path("/Applications/Claude.app/Contents/MacOS/Claude")


def executable(value):
    path = Path(value).expanduser().absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("helper must be an executable file: " + str(path))
    home = Path.home()
    resolved = path.resolve()
    for folder in ("Desktop", "Documents", "Downloads", "Library/CloudStorage", "Library/Mobile Documents"):
        if resolved == home / folder or home / folder in resolved.parents:
            raise ValueError("helper is in a TCC-protected folder: " + str(path))
    return str(path)


def render(gh=None):
    gh = executable(gh or shutil.which("gh") or "/missing/gh")
    helper = executable(ROOT / "bin/ghcp-mcp-headers")
    config = json.loads((ROOT / "config/ghcp.json").read_text())
    config["inferenceCredentialHelper"] = gh
    config["managedMcpServers"][0]["headersHelper"] = helper
    config["managedMcpServers"][0]["headersHelperArgs"] = [gh]
    return config


def isolated_path(value):
    path = Path(value).expanduser().absolute()
    resolved = path.resolve()
    if not path.name.endswith("-3p") or not resolved.name.endswith("-3p"):
        raise ValueError("isolated profile directory must end in -3p")
    support = (Path.home() / "Library/Application Support").resolve()
    for candidate in (path, resolved):
        if candidate == support or support in candidate.parents:
            relative = candidate.relative_to(support)
            if not relative.parts or relative.parts[0].startswith("Claude"):
                raise ValueError("refusing the real Claude application-support profiles")
        for forbidden in (Path.home() / ".claude", Path("/Library/Managed Preferences")):
            if candidate == forbidden or forbidden in candidate.parents:
                raise ValueError("refusing a shared configuration directory")
    return resolved


def write_json(path, value):
    if path.is_symlink():
        raise ValueError("refusing symlink: " + str(path))
    temporary = path.with_name(path.name + "." + str(uuid.uuid4()) + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    temporary.replace(path)


def install(path, config):
    library = path / "configLibrary"
    if library.is_symlink():
        raise ValueError("refusing symlinked configLibrary")
    library.mkdir(parents=True, exist_ok=True, mode=0o700)
    meta_path = library / "_meta.json"
    if meta_path.is_symlink():
        raise ValueError("refusing symlinked metadata")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"appliedId": "", "entries": []}
    if not isinstance(meta.get("entries"), list):
        raise ValueError("invalid configLibrary metadata; entries must be an array")
    identifier = str(uuid.uuid4())
    write_json(library / (identifier + ".json"), config)
    if meta_path.exists():
        write_json(library / ("_meta.backup-" + identifier + ".json"), meta)
    meta["entries"].append({"id": identifier, "name": "GitHub Copilot"})
    meta["appliedId"] = identifier
    write_json(meta_path, meta)
    return library / (identifier + ".json")


def auth_preflight(config):
    result = subprocess.run([config["inferenceCredentialHelper"], "auth", "token", "--hostname", "github.com"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, timeout=30, check=False)
    if result.returncode:
        raise ValueError("GitHub CLI authentication unavailable; run gh auth login --hostname github.com, "
                         "select the intended active account with gh auth switch --hostname github.com --user USERNAME")


def processes():
    output = subprocess.check_output(["/bin/ps", "-axo", "pid=,command="], text=True)
    result = []
    for line in output.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2:
            result.append((int(fields[0]), fields[1]))
    return result


def matches(command, profile):
    # ps does not escape spaces in argv on macOS; require a full option boundary
    # and a real Claude executable, never a shell/our own script mentioning it.
    app_prefix = str(APP)
    helper_prefix = "/Applications/Claude.app/Contents/Frameworks/Claude Helper"
    if not (command.startswith(app_prefix + " ") or command.startswith(helper_prefix)):
        return False
    option = "--user-data-dir=" + str(profile)
    return re.search(r"(?:^|\s)" + re.escape(option) + r"(?=\s--|$)", command) is not None


def matching_pids(profile):
    return [pid for pid, command in processes() if matches(command, profile)]


def protected_snapshot(pid):
    rows = dict(processes())
    if pid not in rows or rows[pid].split(" --", 1)[0] != str(APP):
        raise ValueError("protected PID is not the running main Claude process")
    config = Path.home() / "Library/Application Support/Claude-3p/claude_desktop_config.json"
    started = subprocess.check_output(["/bin/ps", "-p", str(pid), "-o", "lstart="], text=True).strip()
    return rows[pid], hashlib.sha1(config.read_bytes()).hexdigest() if config.exists() else None, started


def assert_protected(pid, before):
    if protected_snapshot(pid) != before:
        raise RuntimeError("STOP: protected Claude process or profile changed")


def launch(profile, protect_pid):
    before = protected_snapshot(protect_pid)
    if matching_pids(profile):
        raise ValueError("isolated instance already running")
    if not (profile / "configLibrary/_meta.json").is_file():
        raise ValueError("install this isolated profile before launching")
    code_dir = profile / "claude-code"
    logs = profile / "logs"
    for path in (code_dir, logs):
        if path.is_symlink():
            raise ValueError("refusing symlinked runtime directory")
        path.mkdir(mode=0o700, exist_ok=True)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(code_dir))
    # Discard shell inference overrides: Desktop must use the installed helper.
    for key in list(env):
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_CODE_USE_"):
            env.pop(key)
    env.pop("CLAUDE_USER_DATA_DIR", None)
    log_path = logs / ("launch-" + str(time.time_ns()) + ".log")
    with log_path.open("x") as log:
        os.chmod(log_path, 0o600)
        process = subprocess.Popen([str(APP), "--user-data-dir=" + str(profile)],
                                   env=env, cwd=profile, stdout=log, stderr=log,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
    time.sleep(3)
    assert_protected(protect_pid, before)
    if process.poll() is not None or process.pid not in matching_pids(profile):
        raise RuntimeError("isolated launch exited; inspect " + str(log_path))
    print(process.pid)


def stop(profile, protect_pid, dry_run=False):
    before = protected_snapshot(protect_pid)
    pids = matching_pids(profile)
    if protect_pid in pids:
        raise ValueError("protected PID matched; refusing stop")
    if dry_run:
        print(json.dumps(pids))
        return
    for pid in pids:
        # Recheck immediately before signaling: no broad process-name matching.
        if pid in matching_pids(profile):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for _ in range(50):
        if not matching_pids(profile):
            break
        time.sleep(0.1)
    assert_protected(protect_pid, before)
    if matching_pids(profile):
        raise RuntimeError("isolated processes remain; no forced kill attempted")
    print(json.dumps({"stopped": pids, "protected_pid": protect_pid, "protected_sha1": before[1]}))


def main(action):
    parser = argparse.ArgumentParser()
    if action != "render-config":
        parser.add_argument("profile")
    if action in ("render-config", "install-isolated"):
        parser.add_argument("--gh")
    if action in ("launch-isolated", "stop-isolated"):
        parser.add_argument("--protect-pid", type=int, required=True)
    if action == "stop-isolated":
        parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if action == "render-config":
        print(json.dumps(render(args.gh), indent=2))
    else:
        profile = isolated_path(args.profile)
        if action == "install-isolated":
            config = render(args.gh)
            auth_preflight(config)
            print(install(profile, config))
        elif action == "launch-isolated":
            launch(profile, args.protect_pid)
        else:
            stop(profile, args.protect_pid, args.dry_run)


def entry(action):
    try:
        main(action)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
