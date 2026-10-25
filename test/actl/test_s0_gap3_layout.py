"""S37-05 (layout.py:31 `<` -> `<=`) and S37-04 (layout.py:38 parents=True -> False)."""
import pytest

from actl.layout import Layout

TAG = "2026-01-02_layout-demo"


@pytest.mark.parametrize("name", ["a b", " ", "  ", "a b c", "~", "a~b", "\u00e9"])
def test_workspace_name_accepts(tmp_path, name):
    lay = Layout(tmp_path / "g")
    p = lay.workspace(name)
    assert p.name == name
    assert lay.workspace(name, TAG).name == name


@pytest.mark.parametrize("name", ["\x1f", "a\x1fb", "\x7f", "a\x7fb", "\x00", "\x01", "\n", "\t"])
def test_workspace_name_rejects_controls(tmp_path, name):
    lay = Layout(tmp_path / "g")
    with pytest.raises(ValueError, match="Invalid workspace name"):
        lay.workspace(name)


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\\b"])
def test_workspace_name_rejects_structural(tmp_path, name):
    lay = Layout(tmp_path / "g")
    with pytest.raises(ValueError, match="Invalid workspace name"):
        lay.workspace(name)


def test_ensure_base_tree_creates_missing_root_parents(tmp_path):
    root = tmp_path / "x" / "y" / "graph"
    assert not root.parent.exists()
    Layout(root).ensure_base_tree()
    assert root.is_dir()
    assert (root / "records").is_dir()
    assert (root / "sprints").is_dir()
    assert (root / "profiles").is_dir()
    assert (root / "repos").is_dir()


def test_ensure_sprint_tree_creates_missing_root_parents(tmp_path):
    root = tmp_path / "p" / "q" / "graph"
    lay = Layout(root)
    lay.ensure_sprint_tree(TAG)
    assert lay.runs_dir(TAG).is_dir()
