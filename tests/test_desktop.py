import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
# Capture the original home lexically, without inspecting either real profile.
REAL_HOME = os.environ.get("HOME")
if not REAL_HOME or not os.path.isabs(REAL_HOME):
    raise RuntimeError("tests require an absolute initial HOME for the safety guard")
PYTHON = str(Path(sys.executable).absolute())
GIT = shutil.which("git")
spec = importlib.util.spec_from_file_location("desktop", ROOT / "scripts/desktop.py")
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
safety_spec = importlib.util.spec_from_file_location("test_safety", ROOT / "tests/sandbox/sitecustomize.py")
safety = importlib.util.module_from_spec(safety_spec)
safety_spec.loader.exec_module(safety)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.env = {
            "HOME": str(self.home), "PATH": str(self.base) + ":/usr/bin:/bin",
            "TMPDIR": str(self.base), "LANG": "en_US.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "tests/sandbox"),
            "GHCP_TEST_HOME": str(self.home), "GHCP_REAL_HOME": REAL_HOME,
            "GHCP_TEST_FORBID_REAL_HOME": "1",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        }
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.assertEqual(Path.home(), self.home)
        safety.install_guard(REAL_HOME, self.home)
        self.addCleanup(safety.disable_guard)
        (self.base / "python3").symlink_to(PYTHON)
        self.gh = self.base / "gh"
        self.gh.write_text("#!/bin/sh\n[ \"$*\" = 'auth token --hostname github.com' ] || exit 2\nprintf '%s\\n' fake-test-credential\n")
        self.gh.chmod(0o755)
        # Enforce explicit sanitized env even for subprocesses called by production
        # functions during unit tests. Nested Python processes load sitecustomize.
        original_popen = subprocess.Popen

        def guarded_popen(*args, **kwargs):
            kwargs.setdefault("env", self.env.copy())
            self.assertEqual(kwargs["env"], self.env)
            self.assertEqual(os.environ.get("HOME"), str(self.home))
            return original_popen(*args, **kwargs)

        popen = patch.object(subprocess, "Popen", side_effect=guarded_popen)
        popen.start()
        self.addCleanup(popen.stop)

    def run_command(self, command):
        for arg in command:
            if os.path.isabs(str(arg)):
                safety.guard_path(arg)
        return subprocess.run(command, capture_output=True, text=True, env=self.env)

    def test_render_executable_paths_and_required_keys(self):
        result = self.run_command([str(ROOT / "scripts/render-config"), "--gh", str(self.gh)])
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(config["inferenceProvider"], "gateway")
        self.assertEqual(config["inferenceGatewayBaseUrl"], "https://api.githubcopilot.com")
        self.assertEqual(config["inferenceGatewayAuthScheme"], "bearer")
        self.assertEqual(config["inferenceCredentialHelperArgs"], ["auth", "token", "--hostname", "github.com"])
        self.assertFalse(config["modelDiscoveryEnabled"])
        self.assertTrue(config["disableDeepLinkRegistration"])
        models = config["inferenceModels"]
        self.assertEqual(models[3:], ["claude-sonnet-5", "claude-haiku-4.5"])
        for entry, tier in zip(models[:3], ("opus", "sonnet", "haiku"), strict=True):
            self.assertEqual(entry["name"], f"claude-{tier}-5.5")
            self.assertEqual(entry["anthropicFamilyTier"], tier)
            self.assertIs(entry["isFamilyDefault"], True)
        for path in (config["inferenceCredentialHelper"], config["managedMcpServers"][0]["headersHelper"]):
            self.assertTrue(Path(path).is_absolute() and os.access(path, os.X_OK))
        self.assertNotIn("fake-test-credential", result.stdout)

    def test_mcp_helper_exact_object_and_failure_redaction(self):
        command = [str(ROOT / "bin/ghcp-mcp-headers"), str(self.gh)]
        result = self.run_command(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"Authorization": "Bearer fake-test-credential"})
        self.assertEqual(len(result.stdout.splitlines()), 1)
        for script in ("printf 'secret-diagnostic' >&2; exit 1", "printf 'two\\nlines'", "exit 0"):
            self.gh.write_text("#!/bin/sh\n" + script + "\n")
            result = self.run_command(command)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("secret-diagnostic", result.stderr)

    def test_install_metadata_and_backup(self):
        profile = desktop.isolated_path(self.base / "Claude-3p")
        config = desktop.render(str(self.gh))
        first = desktop.install(profile, config)
        second = desktop.install(profile, config)
        meta = json.loads((profile / "configLibrary/_meta.json").read_text())
        self.assertEqual(meta["appliedId"], second.stem)
        self.assertEqual(len(meta["entries"]), 2)
        self.assertEqual(json.loads(first.read_text()), config)
        self.assertEqual(len(list(first.parent.glob("_meta.backup-*.json"))), 1)

    def test_refuses_profile_locations_under_fixture_home(self):
        forbidden = [self.base / "Claude", self.home / "Library/Application Support/Claude",
                     self.home / "Library/Application Support/Claude-3p",
                     self.home / "Library/Application Support/Claude-other/nested-3p"]
        link = self.base / "linked-3p"
        link.symlink_to(forbidden[2])
        for target in forbidden + [link]:
            result = self.run_command([str(ROOT / "scripts/install-isolated"), str(target), "--gh", str(self.gh)])
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_refuses_symlinked_library(self):
        profile = self.base / "Claude-3p"
        profile.mkdir()
        (profile / "configLibrary").symlink_to(self.base)
        with self.assertRaises(ValueError):
            desktop.install(profile, desktop.render(str(self.gh)))

    def test_stop_signals_only_exact_isolated_claude(self):
        profile = self.base / "Space Here-3p"
        app = str(desktop.APP)
        # Synthetic process table: none of these PIDs is queried or signaled.
        rows = [(101, app), (444, app + " --user-data-dir=" + str(profile)),
                (445, app + " --user-data-dir=" + str(profile) + "-other"),
                (446, "/bin/sh -c " + app + " --user-data-dir=" + str(profile)),
                (447, app + " --user-data-dir=" + str(profile) + " extra"),
                (448, app + " --user-data-dir=" + str(self.base / "another-3p")),
                (449, app + " --user-data-dir=" + str(profile) + "/child --test"),
                (450, app + " --user-data-dir=" + str(profile) + " extra --test"),
                (451, "/Applications/Claude.app/Contents/Frameworks/Claude Helper (GPU).app/Contents/MacOS/Claude Helper (GPU) --type=gpu-process --user-data-dir=" + str(profile) + " --test"),
                (452, "/Applications/Claude.app/Contents/Frameworks/Claude Helper (Renderer).app/Contents/MacOS/Claude Helper (Renderer) --user-data-dir=" + str(profile)),
                (453, app + " --user-data-dir=" + str(profile) + "-other --test")]
        with patch.object(desktop, "processes", return_value=rows):
            self.assertEqual(desktop.matching_pids(profile), [444, 451, 452])
        snapshot = (app, "digest", "Mon Jan 01 00:00:00 2024")
        with patch.object(desktop, "protected_snapshot", return_value=snapshot), \
             patch.object(desktop, "matching_pids", side_effect=[[444], [444], [], []]), \
             patch.object(desktop.os, "kill") as kill:
            desktop.stop(profile, 101)
            kill.assert_called_once_with(444, desktop.signal.SIGTERM)

    def test_no_token_like_content(self):
        prefixes = tuple("gh" + c + "_" for c in "pousr") + ("github" + "_pat_", "sk" + "-ant")
        result = self.run_command([GIT, "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"])
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in result.stdout.splitlines():
            path = ROOT / name
            if path.exists():  # Tracked deletions are expected during this change.
                self.assertFalse(any(prefix.encode() in path.read_bytes() for prefix in prefixes), name)

    def test_isolated_install_token_preflight(self):
        target = self.base / "isolated-3p"
        command = [str(ROOT / "scripts/install-isolated"), str(target), "--gh", str(self.gh)]
        self.gh.write_text("#!/bin/sh\nprintf 'secret-diagnostic' >&2\nexit 1\n")
        result = self.run_command(command)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh auth login", result.stderr)
        self.assertNotIn("secret-diagnostic", result.stderr)
        self.assertFalse(target.exists())
        self.gh.write_text("#!/bin/sh\n[ \"$*\" = 'auth token --hostname github.com' ] || exit 2\nprintf fake-test-credential\n")
        result = self.run_command(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("fake-test-credential", result.stdout + result.stderr)
        self.assertTrue((target / "configLibrary/_meta.json").is_file())
        with patch.object(desktop.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            desktop.auth_preflight(desktop.render(str(self.gh)))
        self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)

    def test_masking_all_github_token_families_and_required_pid(self):
        with patch.dict(sys.modules, {"desktop": desktop}):
            live_spec = importlib.util.spec_from_file_location("live_check", ROOT / "scripts/live-check.py")
            live = importlib.util.module_from_spec(live_spec)
            live_spec.loader.exec_module(live)
        tokens = ["gh" + c + "_synthetic123" for c in "pousr"] + ["github" + "_pat_synthetic123", "sk" + "-ant-synthetic123"]
        self.assertEqual(live.mask(" ".join(tokens)), " ".join(["[REDACTED]"] * len(tokens)))
        result = self.run_command([PYTHON, str(ROOT / "scripts/live-check.py"), "baseline", "--profile", str(self.base / "x-3p"), "--evidence", str(self.base / "evidence")])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--protect-pid", result.stderr)

    def test_guard_blocks_real_profile_paths_in_parent_and_child(self):
        # No profile access: lexical rejection happens before resolve/open, and
        # the resolved-alias case uses a mocked resolver rather than a real link.
        forbidden = Path(REAL_HOME) / "Library/Application Support/Claude-3p/config.json"
        with self.assertRaisesRegex(AssertionError, "real Claude profile"):
            safety.guard_path(forbidden)
        with patch.object(Path, "resolve", return_value=forbidden), \
             self.assertRaisesRegex(AssertionError, "real Claude profile"):
            safety.guard_path(self.base / "alias")
        result = self.run_command([PYTHON, "-c", "import os; open(os.environ['GHCP_REAL_HOME'] + '/Library/Application Support/Claude-3p/config.json')"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("real Claude profile", result.stderr)
        self.assertNotIn("FileNotFoundError", result.stderr)
        self.assertFalse(any(key in self.env for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_CONFIG_DIR", "CLAUDE_CONFIG_DIR")))

    def test_write_json_private_at_creation(self):
        path = self.base / "private.json"
        with patch.object(desktop.os, "open", wraps=os.open) as open_file:
            desktop.write_json(path, {"value": True})
        self.assertEqual(open_file.call_args.args[2], 0o600)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_guard_blocks_real_code_settings_parent_and_child(self):
        for suffix in (".claude", ".claude/settings.json", ".claude.json"):
            forbidden = Path(REAL_HOME) / suffix
            with self.assertRaisesRegex(AssertionError, "Claude Code settings"):
                safety.guard_path(forbidden)
            with patch.object(Path, "resolve", return_value=forbidden), self.assertRaisesRegex(AssertionError, "Claude Code settings"):
                safety.guard_path(self.base / "alias")
            code = "import os; open(os.environ['GHCP_REAL_HOME'] + '/' + " + repr(suffix) + ")"
            result = self.run_command([PYTHON, "-c", code])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Claude Code settings", result.stderr)


if __name__ == "__main__":
    unittest.main()
