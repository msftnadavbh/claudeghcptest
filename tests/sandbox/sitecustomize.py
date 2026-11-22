"""Test-only profile I/O tripwire, also loaded by every Python subprocess."""
import os
from pathlib import Path
import sys

_real_home = None
_fixture_home = None
_installed = False


def reject_real(path):
    if not _real_home or not isinstance(path, (str, bytes, os.PathLike)):
        return
    value = os.path.normpath(os.path.abspath(os.fsdecode(path))).casefold()
    support = os.path.join(_real_home, "Library", "Application Support").casefold() + os.sep
    if value.startswith(support) and value[len(support):].split(os.sep)[0].startswith("claude"):
        raise AssertionError("test attempted access to a real Claude profile")


def guard_path(path):
    reject_real(path)  # Do not even resolve a literal protected path.
    reject_real(Path(path).resolve())


def audit(event, args):
    if _fixture_home is None:
        return
    if os.environ.get("HOME") != _fixture_home:
        raise AssertionError("test HOME escaped its fixture")
    positions = {
        "open": (0,), "os.listdir": (0,), "os.scandir": (0,),
        "os.mkdir": (0,), "os.remove": (0,), "os.rmdir": (0,),
        "os.rename": (0, 1), "os.symlink": (0, 1), "os.link": (0, 1),
        "os.chmod": (0,), "os.truncate": (0,),
    }
    for index in positions.get(event, ()):
        if isinstance(args[index], (str, bytes, os.PathLike)):
            guard_path(os.fsdecode(args[index]))
    if event == "subprocess.Popen":
        env = args[3]
        if env is None or env.get("HOME") != _fixture_home:
            raise AssertionError("subprocess requires explicit fixture HOME")


def install_guard(real_home, fixture_home):
    global _real_home, _fixture_home, _installed
    _real_home, _fixture_home = str(real_home), str(fixture_home)
    if _fixture_home == _real_home or os.environ.get("HOME") != _fixture_home:
        raise AssertionError("test requires a distinct temporary HOME")
    if not _installed:
        sys.addaudithook(audit)
        _installed = True


def disable_guard():
    global _fixture_home
    _fixture_home = None


if os.environ.get("GHCP_TEST_HOME"):
    install_guard(os.environ["GHCP_REAL_HOME"], os.environ["GHCP_TEST_HOME"])
    import subprocess

    _popen = subprocess.Popen

    class FixturePopen(_popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("env", dict(os.environ))
            super().__init__(*args, **kwargs)

    subprocess.Popen = FixturePopen
