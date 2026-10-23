# Authored-by: Gemini, Owner-attested
import os
import sys
import importlib
from pathlib import Path
import pytest

def _get_hashing():
    repo = os.environ.get("ACTL_REPO")
    if repo:
        src_path = str(Path(repo) / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        # Invalidate cached module if pointing to different repo
        if "actl.hashing" in sys.modules:
            del sys.modules["actl.hashing"]
        if "actl" in sys.modules:
            del sys.modules["actl"]
    return importlib.import_module("actl.hashing")

def test_canonical_json_rejects_nan_and_inf_inside_tuples():
    h = _get_hashing()
    for bad in (float("nan"), float("inf"), float("-inf")):
        for obj in ({"a": (bad,)}, [(bad,)], {"a": [(1, (bad,))]}):
            with pytest.raises(ValueError):
                h.canonical_json(obj)
