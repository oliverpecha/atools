
import pytest
from actl import layout

def test_layout_rejects_symlink_traversal(tmp_path):
    root = tmp_path / "actl-root"
    outside = tmp_path / "outside-target"
    outside.mkdir(parents=True)
    lay = layout.Layout(root)
    
    # Create symlink escaping root
    ws_dir = lay.root / 'workspaces'
    ws_dir.mkdir(parents=True)
    escape_link = ws_dir / "escape"
    escape_link.symlink_to(outside, target_is_directory=True)
    
    with pytest.raises(ValueError, match="Path escapes boundary|outside"):
        lay.workspace("escape")
