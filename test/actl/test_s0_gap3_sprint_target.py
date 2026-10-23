"""S37-11: sprint.init_target guard (sprint.py:95 `or` -> `and`)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

import actl
from actl import sprint
from actl.layout import Layout


@pytest.mark.parametrize("bad", ["", 5, None, "a\x00b", 0, 1.5, b"/tmp", ["x"]])
def test_init_target_invalid_raises_value_error(tmp_path, bad):
    root = tmp_path / "g"
    with pytest.raises(ValueError, match="Invalid target"):
        sprint.init_target(Layout(root), bad)
    assert not root.exists()


def test_cli_init_empty_target_exits_2(tmp_path):
    src = Path(actl.__file__).resolve().parents[1]
    env = dict(os.environ, ACTL_ROOT=str(tmp_path / "g"), PYTHONPATH=str(src))
    code = "import sys; from actl.cli import main; sys.exit(main(sys.argv[1:]))"
    r = subprocess.run(
        [sys.executable, "-c", code, "init", "--target", ""],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "Invalid target" in (r.stdout + r.stderr)
