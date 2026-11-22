"""Config-library-only installation for the installed macOS Desktop."""
import argparse
import contextlib
import copy
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import uuid

import desktop

STATE = ".ghcp-state.json"
OWNER = "_ghcpOwner"
MAIN = re.compile(r"^/.*\.app/Contents/MacOS/Claude$")


def account_home():
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def no_symlinks(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("refusing symlink: " + str(part))


def default_target(sandbox=False):
    home = Path.home()
    if not home.is_absolute():
        raise ValueError("HOME must be absolute")
    target = home / "Library/Application Support/Claude-3p/configLibrary"
    real = account_home().resolve()
    if os.environ.get("GHCP_TEST_FORBID_REAL_HOME") == "1":
        # Check lexically before resolving so the tripwire never visits a real
        # profile. An explicit sandbox HOME may itself live in the account home.
        candidate = Path(os.path.abspath(target))
        if candidate == real or real / "Library" in candidate.parents or home == real:
            raise ValueError("test guard: refusing real HOME configuration")
    no_symlinks(target)
    target = target.resolve()
    if os.environ.get("GHCP_TEST_FORBID_REAL_HOME") == "1" and real / "Library" in target.parents:
        raise ValueError("test guard: refusing resolved real HOME configuration")
    if sandbox:
        if home.resolve() == real or real / "Library" in home.resolve().parents:
            raise ValueError("--sandbox-home requires a distinct HOME outside the account Library")
    elif home.resolve() != real and not (os.environ.get("GHCP_TEST_HOME") == str(home)
                                         and os.environ.get("GHCP_TEST_FORBID_REAL_HOME") == "1"):
        raise ValueError("HOME differs from the account home; use --sandbox-home for validation")
    return target


def same_path(left, right):
    a, b = Path(left).resolve(), Path(right).resolve()
    # Conservative on case-sensitive disks, safe on default case-insensitive APFS.
    return str(a).casefold() == str(b).casefold() or (a.exists() and b.exists() and a.samefile(b))


def process_arguments(pid):
    """Read actual argv on macOS: ps joins arguments without quoting spaces."""
    libc = ctypes.CDLL(None, use_errno=True)
    mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2
    size = ctypes.c_size_t(1024 * 1024)
    buffer = ctypes.create_string_buffer(size.value)
    if libc.sysctl(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
        raise ValueError("cannot inspect Claude arguments; Quit Claude Desktop and re-run")
    raw = buffer.raw[:size.value]
    argc = int.from_bytes(raw[:4], sys.byteorder)
    position = raw.index(b"\0", 4) + 1
    while position < len(raw) and raw[position] == 0:
        position += 1
    arguments = raw[position:].split(b"\0")[:argc]
    if not arguments or len(arguments) != argc or not all(arguments):
        raise ValueError("ambiguous Claude arguments; Quit Claude Desktop and re-run")
    return [os.fsdecode(arg) for arg in arguments]


def blocks_default(arguments, home, sandbox=False):
    if not arguments or not MAIN.fullmatch(arguments[0]):
        return True
    values = []
    for index, argument in enumerate(arguments[1:], 1):
        if argument == "--user-data-dir":
            values.append(arguments[index + 1] if index + 1 < len(arguments) else "")
        elif argument.startswith("--user-data-dir="):
            values.append(argument.split("=", 1)[1])
    if not values:
        # Unqualified launches belong to the OS account, not a caller's HOME.
        return not sandbox
    if len(values) != 1 or not values[0] or not Path(values[0]).is_absolute():
        return True
    base = home / "Library/Application Support/Claude"
    return same_path(values[0], base) or same_path(values[0], Path(str(base) + "-3p"))


def refuse_running(sandbox=False):
    for pid, command in desktop.processes():
        # Also recognize renamed bundles; Helpers have a different executable.
        if re.match(r"^/.*?\.app/Contents/MacOS/Claude(?:\s(?!Helper(?:\s|$))|$)", command):
            if blocks_default(process_arguments(pid), Path.home(), sandbox):
                raise ValueError("Quit Claude Desktop and re-run")


def refuse_mdm():
    managed = Path("/Library/Managed Preferences")
    name = "com.anthropic.claudefordesktop.plist"
    for path in (managed / name, managed / pwd.getpwuid(os.getuid()).pw_name / name):
        if path.exists() or path.is_symlink():
            raise ValueError("Managed (MDM) Claude configuration overrides the local library; refusing: " + str(path))


def read_object(path, fallback):
    no_symlinks(path)
    value = json.loads(path.read_text()) if path.exists() else fallback
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: " + str(path))
    return value


def load(library):
    meta = read_object(library / "_meta.json", {})
    entries = meta.get("entries", [])
    if not isinstance(entries, list) or any(not isinstance(e, dict) or not isinstance(e.get("id"), str) for e in entries):
        raise ValueError("invalid configLibrary entries")
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("duplicate configLibrary entry IDs")
    state = {}
    try:
        state = read_object(library / STATE, {})
        if (library / STATE).exists():
            validate_state(library, meta, state)
        elif any(OWNER in e for e in entries):
            raise ValueError("ownership entry exists without state")
    except (ValueError, TypeError, KeyError) as error:
        pointer = state.get("backup") if isinstance(state, dict) else None
        raise ValueError("Invalid GHCP state: " + str(error) + "; refusing changes. Recover from backup: "
                         + (str(pointer) if pointer else str(library) + ".backup-<UTC> (if present)")) from error
    return meta, state


def config_hash(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_state(library, meta, state):
    required = {"version", "id", "owner", "library", "configHashes", "previousAppliedIdPresent",
                "previousAppliedId", "libraryExisted", "metaExisted", "entriesExisted", "backup", "timestamp"}
    if set(state) != required or type(state["version"]) is not int or state["version"] != 2:
        raise ValueError("incomplete or unsupported state schema")
    for key in ("id", "owner"):
        if not isinstance(state[key], str) or str(uuid.UUID(state[key])) != state[key]:
            raise ValueError("invalid " + key)
    if state["library"] != str(library.resolve()):
        raise ValueError("state belongs to another library")
    for key in ("previousAppliedIdPresent", "libraryExisted", "metaExisted", "entriesExisted"):
        if type(state[key]) is not bool:
            raise ValueError("invalid " + key)
    if state["previousAppliedId"] is not None and not isinstance(state["previousAppliedId"], str):
        raise ValueError("invalid previous selector")
    if not state["previousAppliedIdPresent"] and state["previousAppliedId"] is not None:
        raise ValueError("inconsistent previous selector")
    timestamp = state["timestamp"]
    if not isinstance(timestamp, str):
        raise ValueError("invalid timestamp")
    datetime.strptime(timestamp, "%Y%m%dT%H%M%S.%fZ")
    expected_backup = str(library.with_name("configLibrary.backup-" + timestamp))
    if state["backup"] != (expected_backup if state["libraryExisted"] else None):
        raise ValueError("invalid backup binding")
    if not state["libraryExisted"] and state["metaExisted"]:
        raise ValueError("inconsistent library origin")
    hashes = state["configHashes"]
    if not isinstance(hashes, list) or not hashes or any(not isinstance(h, str) or not re.fullmatch(r"[a-f0-9]{64}", h) for h in hashes):
        raise ValueError("invalid config provenance")
    own = library / (state["id"] + ".json")
    no_symlinks(own)
    if own.exists() and config_hash(read_object(own, {})) not in hashes:
        raise ValueError("owned config was replaced or edited")
    entry = next((e for e in meta.get("entries", []) if e["id"] == state["id"]), None)
    if entry is not None and entry.get(OWNER) != state["owner"]:
        raise ValueError("entry ownership mismatch")


def sync_path(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def backup_library(library, backup):
    for root, dirs, files in os.walk(library, followlinks=False):
        for name in dirs + files:
            path = Path(root) / name
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError("unsupported library backup entry: " + str(path))
    partial = backup.with_name(backup.name + ".partial-" + str(uuid.uuid4()))
    partial.mkdir(mode=0o700)
    try:
        # Copy children, not the root's potentially permissive mode.
        for child in library.iterdir():
            if child.is_dir():
                shutil.copytree(child, partial / child.name, symlinks=True)
            else:
                shutil.copy2(child, partial / child.name, follow_symlinks=False)
        for root, dirs, files in os.walk(partial, topdown=False):
            for name in files:
                sync_path(Path(root) / name)
            sync_path(Path(root))
        if backup.exists():
            raise ValueError("backup destination already exists")
        partial.rename(backup)
        sync_path(backup.parent)
    finally:
        if partial.exists():
            shutil.rmtree(partial)


def file_snapshot(paths):
    result = {}
    for path in paths:
        no_symlinks(path)
        result[path] = path.read_bytes() if path.exists() else None
    return result


@contextlib.contextmanager
def library_lock(library):
    descriptor = os.open(library, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another config-library operation is running")
        yield
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def change(action, gh=None, dry_run=False, sandbox=False):
    library = default_target(sandbox)
    refuse_mdm()
    refuse_running(sandbox)
    config = desktop.render(gh) if action == "install" else None
    if config is not None:
        desktop.auth_preflight(config)
    existed = library.exists()
    meta, state = load(library)
    snapshot = copy.deepcopy((meta, state))
    if action == "uninstall" and not state:
        print("No managed GitHub Copilot installation found at " + str(library))
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = library.with_name("configLibrary.backup-" + timestamp) if existed else None
    note = None
    if action == "install":
        if not state:
            state = {"version": 2, "id": str(uuid.uuid4()), "owner": str(uuid.uuid4()),
                     "library": str(library), "configHashes": [],
                     "previousAppliedIdPresent": "appliedId" in meta,
                     "previousAppliedId": meta.get("appliedId"), "libraryExisted": existed,
                     "metaExisted": (library / "_meta.json").exists(), "entriesExisted": "entries" in meta,
                     "backup": str(backup) if backup else None, "timestamp": timestamp}
        digest = config_hash(config)
        if digest not in state["configHashes"]:
            state["configHashes"].append(digest)
        identifier = state["id"]
        entries = meta.setdefault("entries", [])
        own = next((e for e in entries if e["id"] == identifier), None)
        if own is None:
            entries.append({"id": identifier, "name": "GitHub Copilot", OWNER: state["owner"]})
        else:
            own["name"] = "GitHub Copilot"
        meta["appliedId"] = identifier
    else:
        identifier = state["id"]
        meta["entries"] = [e for e in meta.get("entries", []) if e["id"] != identifier]
        if meta.get("appliedId") == identifier:
            previous = state["previousAppliedId"]
            meta.pop("appliedId", None)
            if state["previousAppliedIdPresent"] and previous:
                candidate = library / (previous + ".json")
                valid = (Path(previous).name == previous and previous not in (".", "..")
                         and any(e["id"] == previous for e in meta["entries"]))
                if valid:
                    no_symlinks(candidate)
                    valid = candidate.is_file()
                if valid:
                    meta["appliedId"] = previous
                else:
                    note = "Previous configuration is unavailable; appliedId left absent instead of restoring a dangling selector."
        if not state["entriesExisted"] and not meta["entries"]:
            meta.pop("entries")
    own_path = library / (identifier + ".json")
    no_symlinks(own_path)
    if not snapshot[1] and own_path.exists():
        raise ValueError("generated UUID collides with an existing file; refusing changes")
    validate_state(library, meta, state)
    expected = file_snapshot([library / STATE, own_path, library / "_meta.json"])
    remove_meta = action == "uninstall" and not state["metaExisted"] and meta in ({}, {"entries": []})
    plan = {"action": action, "library": str(library), "backup": str(backup) if backup else None,
            "config": {"path": str(own_path), "operation": "write" if config else "remove"},
            "metadata": {"operation": "remove" if remove_meta else "merge", "value": meta},
            "state": {"operation": "write" if config else "remove", "value": state},
            "removeLibraryIfEmpty": action == "uninstall" and not state["libraryExisted"]}
    if config:
        plan["config"]["value"] = config
    if note:
        plan["note"] = note
    if dry_run:
        print(json.dumps(plan, indent=2))
        return
    refuse_running(sandbox)
    no_symlinks(library)
    library.mkdir(parents=True, exist_ok=True, mode=0o700)
    with library_lock(library):
        if load(library) != snapshot:
            raise ValueError("configLibrary changed; re-run")
        if backup:
            backup_library(library, backup)
        sync_path(library.parent)

        def publish(path, value=None, remove=False):
            # Snapshot includes config bytes, not only metadata/state; update the
            # expected image after each of our own completed publications.
            refuse_running(sandbox)
            no_symlinks(library)
            if file_snapshot(expected) != expected:
                raise ValueError("configLibrary changed before publication; refusing changes; inspect backup: "
                                 + str(backup or state["backup"]))
            if remove:
                path.unlink(missing_ok=True)
            else:
                desktop.write_json(path, value)
            sync_path(library)
            expected[path] = path.read_bytes() if path.exists() else None

        if config:
            # Directory barriers order recovery state, config, then selector.
            publish(library / STATE, state)
            publish(own_path, config)
            publish(library / "_meta.json", meta)
        else:
            publish(library / "_meta.json", meta, remove=remove_meta)
            publish(own_path, remove=True)
            # Retain recovery state until selector and config deletion are durable.
            publish(library / STATE, remove=True)
    if action == "uninstall" and not state["libraryExisted"] and not any(library.iterdir()):
        library.rmdir()
        sync_path(library.parent)
    print("Config library: " + str(library))
    print("Backup: " + (str(backup) if backup else "none; configLibrary did not exist"))
    if config:
        print("Open Claude Desktop — it starts in third-party mode on GitHub Copilot")
        print("To revert: quit Claude Desktop, then run ./uninstall")
    else:
        if note:
            print(note)
        print("GitHub Copilot configuration removed; later selection preserved or previous selection restored when available. Open Claude Desktop.")


def entry(action):
    parser = argparse.ArgumentParser(description=("Configure your installed Claude Desktop for GitHub Copilot."
                                                if action == "install" else "Restore your previous Desktop configuration selection."))
    parser.add_argument("--dry-run", action="store_true", help="print exact planned changes without writing")
    parser.add_argument("--sandbox-home", action="store_true", help="validate with a separate HOME; exclude the OS account's unqualified app")
    if action == "install":
        parser.add_argument("--gh", help="absolute GitHub CLI executable path")
        parser.add_argument("--isolated", nargs="?", const=str(Path.home() / "claude-ghcp-test/Isolated-3p"), metavar="DIR",
                            help="use the existing separate-profile installer (DIR must end in -3p)")
    args = parser.parse_args()
    try:
        if action == "install" and args.isolated:
            profile = desktop.isolated_path(args.isolated)
            config = desktop.render(args.gh)
            desktop.auth_preflight(config)
            if args.dry_run:
                print(json.dumps({"isolatedProfile": str(profile), "config": config,
                                  "changes": "create a UUID config, append its entry and select it; back up existing metadata"}, indent=2))
            else:
                print(desktop.install(profile, config))
                print("Launch with scripts/launch-isolated \"" + str(profile) + "\" --protect-pid <normal-main-PID>")
        else:
            change(action, getattr(args, "gh", None), args.dry_run, args.sandbox_home)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
