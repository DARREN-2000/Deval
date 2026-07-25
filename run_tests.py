"""Zero-dependency test runner (used when pytest is unavailable offline).

Implements the tiny slice of the pytest API our tests use: tmp_path, capsys,
and plain assert-based test functions discovered in tests/test_*.py.
"""
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))


class _Captured:
    def __init__(self, out, err):
        self.out = out
        self.err = err


class _CapSys:
    def __init__(self):
        self._out = io.StringIO()
        self._err = io.StringIO()

    def readouterr(self):
        out, err = self._out.getvalue(), self._err.getvalue()
        self._out = io.StringIO()
        self._err = io.StringIO()
        return _Captured(out, err)


def _make_arg(name, capsys_holder):
    if name == "tmp_path":
        return Path(tempfile.mkdtemp(prefix="deval-test-"))
    if name == "capsys":
        cs = _CapSys()
        capsys_holder.append(cs)
        return cs
    raise RuntimeError(f"unsupported fixture: {name}")


def run():
    test_files = sorted((ROOT / "tests").glob("test_*.py"))
    passed = failed = 0
    failures = []
    for tf in test_files:
        spec = importlib.util.spec_from_file_location(tf.stem, tf)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[tf.stem] = mod
        spec.loader.exec_module(mod)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            code = fn.__code__
            argnames = code.co_varnames[: code.co_argcount]
            capsys_holder = []
            try:
                args = [_make_arg(a, capsys_holder) for a in argnames]
            except RuntimeError as exc:
                failures.append((tf.name, name, f"fixture error: {exc}"))
                failed += 1
                continue
            buf_out, buf_err = io.StringIO(), io.StringIO()
            try:
                if capsys_holder:
                    cs = capsys_holder[0]
                    with redirect_stdout(cs._out), redirect_stderr(cs._err):
                        fn(*args)
                else:
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        fn(*args)
                passed += 1
                print(f"  PASS {tf.name}::{name}")
            except Exception:
                failed += 1
                failures.append((tf.name, name, traceback.format_exc()))
                print(f"  FAIL {tf.name}::{name}")
    print(f"\n{passed} passed, {failed} failed")
    for tf, name, tb in failures:
        print(f"\n=== {tf}::{name} ===\n{tb}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
