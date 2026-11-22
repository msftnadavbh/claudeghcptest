import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_desktop

ROOT, desktop = test_desktop.ROOT, test_desktop.desktop

with patch.dict(sys.modules, {"desktop": desktop}):
    spec = importlib.util.spec_from_file_location("config_modes", ROOT / "scripts/config_modes.py")
    modes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modes)


class ModeTests(unittest.TestCase):
    run_command = test_desktop.DesktopTests.run_command

    def setUp(self):
        test_desktop.DesktopTests.setUp(self)
        self.library = self.home / "Library/Application Support/Claude-3p/configLibrary"
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(modes, "refuse_running"))
        self.stack.enter_context(patch.object(modes, "refuse_mdm"))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def change(self, action="install", **kwargs):
        modes.change(action, str(self.gh), **kwargs)

    def seed(self):
        self.library.mkdir(parents=True)
        meta = {"entries": [{"id": "foreign", "name": "Customer", "extra": [1]}],
                "appliedId": "foreign", "custom": {"keep": True}}
        desktop.write_json(self.library / "_meta.json", meta)
        (self.library / "foreign.json").write_text('{"foreign":true}\n')
        return meta

    def test_default_resolution_and_test_guard(self):
        self.assertEqual(modes.default_target(), self.library)
        with patch.object(modes, "account_home", return_value=self.home):
            with self.assertRaisesRegex(ValueError, "test guard"):
                modes.default_target()

    def test_running_main_argument_cases(self):
        base = self.home / "Library/Application Support/Claude"
        for app in ("/Applications/Claude.app/Contents/MacOS/Claude",
                    str(self.home / "Applications/Claude.app/Contents/MacOS/Claude"),
                    "/Volumes/Apps/Renamed.app/Contents/MacOS/Claude"):
            for args in ([], ["--user-data-dir=" + str(base)], ["--user-data-dir", str(base)],
                         ["--user-data-dir=" + str(base) + "-3p"], ["--user-data-dir=relative"],
                         ["--user-data-dir"], ["--user-data-dir=/tmp/a", "--user-data-dir=/tmp/b"],
                         ["--user-data-dir=" + str(base).lower()]):
                self.assertTrue(modes.blocks_default([app] + args, self.home), args)
            self.assertFalse(modes.blocks_default([app, "--user-data-dir=" + str(self.base / "isolated-3p")], self.home))
            self.assertFalse(modes.blocks_default([app], self.home, sandbox=True))
            self.assertTrue(modes.blocks_default([app, "--user-data-dir=" + str(base)], self.home, sandbox=True))

    def test_process_discovery_ignores_helpers_only(self):
        self.stack.close()
        apps = ["/Applications/Claude.app/Contents/MacOS/Claude",
                str(self.home / "Applications/Claude.app/Contents/MacOS/Claude"),
                "/Volumes/Apps/Renamed.app/Contents/MacOS/Claude"]
        for app in apps:
            with patch.object(desktop, "processes", return_value=[(400, app)]), \
                 patch.object(modes, "process_arguments", return_value=[app]), \
                 self.assertRaisesRegex(ValueError, "Quit Claude Desktop and re-run"):
                modes.refuse_running()
        helper = "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper --type=gpu-process"
        with patch.object(desktop, "processes", return_value=[(401, helper)]), \
             patch.object(modes, "process_arguments") as arguments:
            modes.refuse_running()
            arguments.assert_not_called()
        with patch.object(desktop, "processes", return_value=[(402, apps[0])]), \
             patch.object(modes, "process_arguments", side_effect=ValueError("Quit Claude Desktop and re-run")), \
             self.assertRaises(ValueError):
            modes.refuse_running()

    def test_mdm_machine_and_user_refusal(self):
        self.stack.close()
        for suffix in ("/Managed Preferences/com.anthropic.claudefordesktop.plist",
                       "/" + modes.pwd.getpwuid(os.getuid()).pw_name + "/com.anthropic.claudefordesktop.plist"):
            with patch.object(Path, "exists", autospec=True, side_effect=lambda p: str(p).endswith(suffix)), \
                 self.assertRaisesRegex(ValueError, "MDM"):
                modes.refuse_mdm()

    def test_backup_merge_idempotency_and_revert(self):
        original = self.seed()
        original_bytes = (self.library / "foreign.json").read_bytes()
        self.change()
        meta, state = modes.load(self.library)
        identifier = state["id"]
        backup = Path(state["backup"])
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads((backup / "_meta.json").read_text()), original)
        self.assertEqual(meta["entries"][0], original["entries"][0])
        self.assertEqual(meta["custom"], original["custom"])
        self.change()
        again, repeated = modes.load(self.library)
        self.assertEqual(state, repeated)
        self.assertEqual(len(again["entries"]), 2)
        self.assertEqual(again["appliedId"], identifier)
        for filename in ("_meta.json", modes.STATE, identifier + ".json"):
            self.assertEqual((self.library / filename).stat().st_mode & 0o777, 0o600)
        self.change("uninstall")
        self.assertEqual(modes.load(self.library), (original, {}))
        self.assertEqual((self.library / "foreign.json").read_bytes(), original_bytes)
        self.assertEqual(sorted(p.name for p in self.library.iterdir()), ["_meta.json", "foreign.json"])

    def test_absent_library_revert_and_missing_selector(self):
        self.change()
        self.assertFalse(modes.load(self.library)[1]["libraryExisted"])
        self.change("uninstall")
        self.assertFalse(self.library.exists())
        self.library.mkdir()
        desktop.write_json(self.library / "_meta.json", {"custom": False})
        self.change()
        self.change("uninstall")
        self.assertEqual(modes.load(self.library)[0], {"custom": False})

    def test_uninstall_preserves_new_foreign_entries(self):
        self.change()
        meta, _ = modes.load(self.library)
        meta["entries"].append({"id": "later", "name": "Later"})
        desktop.write_json(self.library / "_meta.json", meta)
        (self.library / "later.json").write_text("{}")
        self.change("uninstall")
        self.assertEqual(modes.load(self.library)[0], {"entries": [{"id": "later", "name": "Later"}]})
        self.assertTrue((self.library / "later.json").exists())

    def test_dry_run_has_no_writes(self):
        before = sorted(str(p) for p in self.home.rglob("*"))
        self.change(dry_run=True)
        self.assertEqual(sorted(str(p) for p in self.home.rglob("*")), before)
        self.seed()
        self.change()
        before = {str(p): p.read_bytes() for p in self.library.parent.rglob("*") if p.is_file()}
        self.change("uninstall", dry_run=True)
        self.assertEqual({str(p): p.read_bytes() for p in self.library.parent.rglob("*") if p.is_file()}, before)

    def test_uninstall_preserves_later_false_metadata_fields(self):
        self.change()
        meta, _ = modes.load(self.library)
        meta["customerFlag"] = False
        desktop.write_json(self.library / "_meta.json", meta)
        self.change("uninstall")
        self.assertEqual(modes.load(self.library)[0], {"customerFlag": False})

    def test_default_symlinks_refused(self):
        self.library.parent.mkdir(parents=True)
        self.library.symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.change()
        self.library.unlink()
        self.library.mkdir()
        for name in ("_meta.json", modes.STATE):
            path = self.library / name
            path.symlink_to(self.base / "missing")
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.change()
            path.unlink()
        self.change()
        _, state = modes.load(self.library)
        path = self.library / (state["id"] + ".json")
        path.unlink()
        path.symlink_to(self.base / "missing")
        for action in ("install", "uninstall"):
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.change(action)

    def test_final_running_recheck_prevents_publication(self):
        self.seed()
        before = (self.library / "_meta.json").read_bytes()
        with patch.object(modes, "refuse_running", side_effect=[None, None, ValueError("Quit Claude Desktop and re-run")]), \
             self.assertRaises(ValueError):
            self.change()
        self.assertEqual((self.library / "_meta.json").read_bytes(), before)
        self.assertFalse((self.library / modes.STATE).exists())

    def test_entrypoint_isolated_legacy_behavior_and_help(self):
        profile = self.base / "secondary-3p"
        for _ in range(2):
            result = self.run_command([str(ROOT / "install"), "--isolated", str(profile), "--gh", str(self.gh)])
            self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads((profile / "configLibrary/_meta.json").read_text())
        self.assertEqual(len(meta["entries"]), 2)
        result = self.run_command([str(ROOT / "install"), "--isolated", "--gh", str(self.gh)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / "claude-ghcp-test/Isolated-3p/configLibrary/_meta.json").exists())
        for command in ("install", "uninstall"):
            result = self.run_command([str(ROOT / command), "--help"])
            self.assertEqual(result.returncode, 0)
            self.assertIn("--dry-run", result.stdout)

    def test_later_selection_and_cleared_selector_survive_uninstall(self):
        self.seed()
        for selected in ("replacement", None):
            self.change()
            meta, state = modes.load(self.library)
            meta["entries"].append({"id": "replacement", "name": "B"})
            desktop.write_json(self.library / "replacement.json", {"foreign": True})
            if selected:
                meta["appliedId"] = selected
            else:
                meta.pop("appliedId")
            # Ordinary UI deletion of the GHCP entry/file is supported.
            meta["entries"] = [e for e in meta["entries"] if e["id"] != state["id"]]
            (self.library / (state["id"] + ".json")).unlink()
            desktop.write_json(self.library / "_meta.json", meta)
            self.change("uninstall")
            restored, _ = modes.load(self.library)
            self.assertEqual(restored.get("appliedId"), selected)
            restored["entries"] = [e for e in restored["entries"] if e["id"] != "replacement"]
            desktop.write_json(self.library / "_meta.json", restored)

    def test_deleted_previous_target_never_restored(self):
        original = self.seed()
        for remove_entry in (False, True):
            desktop.write_json(self.library / "_meta.json", original)
            desktop.write_json(self.library / "foreign.json", {})
            self.change()
            meta, _ = modes.load(self.library)
            if remove_entry:
                meta["entries"] = [e for e in meta["entries"] if e["id"] != "foreign"]
                desktop.write_json(self.library / "_meta.json", meta)
            else:
                (self.library / "foreign.json").unlink()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.change("uninstall")
            self.assertNotIn("appliedId", modes.load(self.library)[0])
            self.assertIn("unavailable", output.getvalue())

    def test_complete_state_validation_and_foreign_collision(self):
        self.seed()
        self.change()
        meta, valid = modes.load(self.library)
        original_foreign = (self.library / "foreign.json").read_bytes()
        corruptions = [{}, {**valid, "version": 1}, {**valid, "library": str(self.base)},
                       {**valid, "backup": "/unrelated"}, {**valid, "timestamp": "yesterday"},
                       {**valid, "previousAppliedId": []}, {**valid, "configHashes": []},
                       {**valid, "owner": str(modes.uuid.uuid4())}]
        for key in valid:
            corruptions.append({k: v for k, v in valid.items() if k != key})
        foreign_uuid = str(modes.uuid.uuid4())
        desktop.write_json(self.library / (foreign_uuid + ".json"), {"customer": True})
        corruptions.append({**valid, "id": foreign_uuid})
        for bad in corruptions:
            desktop.write_json(self.library / modes.STATE, bad)
            for action in ("install", "uninstall"):
                with self.assertRaisesRegex(ValueError, "Recover from backup"):
                    self.change(action)
            self.assertEqual((self.library / "foreign.json").read_bytes(), original_foreign)
        (self.library / modes.STATE).write_text("{broken")
        with self.assertRaisesRegex(ValueError, "Recover from backup"):
            self.change()
        desktop.write_json(self.library / modes.STATE, valid)
        desktop.write_json(self.library / (valid["id"] + ".json"), {"replaced": True})
        with self.assertRaisesRegex(ValueError, "replaced or edited"):
            self.change("uninstall")

    def test_missing_state_with_owner_entry_refuses(self):
        self.change()
        (self.library / modes.STATE).unlink()
        with self.assertRaisesRegex(ValueError, "without state"):
            self.change()

    def test_json_failure_cleanup(self):
        path = self.base / "atomic.json"
        path.write_text("original")
        for operation in ("fsync", "replace", "dump"):
            target = {"fsync": desktop.os, "replace": Path, "dump": desktop.json}[operation]
            with patch.object(target, operation, side_effect=OSError("disk failure")), self.assertRaises(OSError):
                desktop.write_json(path, {"value": True})
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(list(self.base.glob("atomic.json.*.tmp")), [])

    def test_backup_failure_never_publishes_complete_name(self):
        self.seed()
        backup = self.library.with_name("configLibrary.backup-test")
        for target, operation in ((modes.shutil, "copy2"), (modes, "sync_path")):
            with patch.object(target, operation, side_effect=OSError("disk failure")), self.assertRaises(OSError):
                modes.backup_library(self.library, backup)
            self.assertFalse(backup.exists())
            self.assertEqual(list(self.library.parent.glob("*.partial-*")), [])

    def test_install_interruption_reuses_owned_id_and_uninstall_recovers(self):
        write = desktop.write_json
        for fail_name in ("config", "_meta.json"):
            calls = []
            def fail(path, value):
                calls.append(path.name)
                if path.name == fail_name or (fail_name == "config" and path.name not in (modes.STATE, "_meta.json")):
                    raise OSError("interruption")
                return write(path, value)
            with patch.object(desktop, "write_json", side_effect=fail), self.assertRaises(OSError):
                self.change()
            _, state = modes.load(self.library)
            self.change()
            self.assertEqual(modes.load(self.library)[1]["id"], state["id"])
            self.change("uninstall")
            self.assertFalse(self.library.exists())

    def test_durable_order_and_uninstall_interruption(self):
        self.seed()
        events = []
        write, sync = desktop.write_json, modes.sync_path
        def record_write(path, value):
            events.append(("write", path.name))
            write(path, value)
        def record_sync(path):
            events.append(("sync", path.name))
            sync(path)
        with patch.object(desktop, "write_json", side_effect=record_write), patch.object(modes, "sync_path", side_effect=record_sync):
            self.change()
        _, state = modes.load(self.library)
        for name in (modes.STATE, state["id"] + ".json", "_meta.json"):
            index = events.index(("write", name))
            self.assertEqual(events[index + 1], ("sync", "configLibrary"))
        state_index = events.index(("write", modes.STATE))
        self.assertTrue(any(kind == "sync" and name.startswith("configLibrary.backup-") for kind, name in events[:state_index]))
        unlink = Path.unlink
        def interrupt(path, *args, **kwargs):
            if path.name == state["id"] + ".json":
                raise OSError("interrupted removal")
            return unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", autospec=True, side_effect=interrupt), self.assertRaises(OSError):
            self.change("uninstall")
        self.assertTrue((self.library / modes.STATE).exists())
        self.assertEqual(modes.load(self.library)[0]["appliedId"], "foreign")
        self.change("uninstall")
        self.assertFalse((self.library / modes.STATE).exists())

    def test_late_snapshot_change_refuses_next_publish(self):
        self.seed()
        write = desktop.write_json
        def edit_after_state(path, value):
            write(path, value)
            if path.name == modes.STATE:
                meta = json.loads((self.library / "_meta.json").read_text())
                meta["customerLater"] = True
                write(self.library / "_meta.json", meta)
        with patch.object(desktop, "write_json", side_effect=edit_after_state), self.assertRaisesRegex(ValueError, "changed before publication"):
            self.change()
        self.assertTrue(modes.load(self.library)[0]["customerLater"])

    def test_test_home_requires_guard(self):
        os.environ["GHCP_TEST_FORBID_REAL_HOME"] = "0"
        try:
            with self.assertRaisesRegex(ValueError, "HOME differs"):
                modes.default_target()
        finally:
            os.environ["GHCP_TEST_FORBID_REAL_HOME"] = "1"

    def test_interrupted_state_removal_is_retryable(self):
        self.seed()
        self.change()
        unlink = Path.unlink
        def interrupt(path, *args, **kwargs):
            if path.name == modes.STATE:
                raise OSError("state removal interruption")
            return unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", autospec=True, side_effect=interrupt), self.assertRaises(OSError):
            self.change("uninstall")
        meta, state = modes.load(self.library)
        self.assertEqual(meta["appliedId"], "foreign")
        self.assertFalse((self.library / (state["id"] + ".json")).exists())
        self.change("uninstall")
        self.assertEqual(modes.load(self.library)[1], {})
