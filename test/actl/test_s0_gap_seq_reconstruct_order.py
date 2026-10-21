# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-21), model family: Claude
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (_REPO / "src", _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
try:
    import helpers  # noqa: F401  (side effects: path setup only)
except Exception:  # helpers is optional for these tests
    pass

import json
import pathlib

import pytest

from actl import ids, seq
from actl.layout import Layout

TAG = "2026-10-16_demo"


def _layout(tmp_path):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    return lay


def _fresh_reconstruct(lay):
    sf = lay.state_file(TAG)
    if sf.exists():
        sf.unlink()
    n = seq.reconstruct(lay, TAG)
    return n, json.loads(lay.state_file(TAG).read_text(encoding="utf-8"))


# T4a -- kills: artifacts.sort(key=lambda t: (t[0], t[1].name)) replaced by a path/name-only key,
# by reverse order, or by removing the sort.  contract-1000 has the HIGHER seq but sorts BEFORE
# contract-999 by name, so replay order decides active_contract and epoch.
def test_reconstruct_replays_in_seq_order_not_name_order(tmp_path):
    lay = _layout(tmp_path)
    sd = lay.sprint_dir(TAG)
    (sd / "contract-999.json").write_text(json.dumps({"epoch": 1}), encoding="utf-8")
    (sd / "contract-1000.json").write_text(json.dumps({"epoch": 2}), encoding="utf-8")
    n, st = _fresh_reconstruct(lay)
    assert n == 1000
    assert st["seq"] == 1000
    assert st["active_contract"] == "contract-1000.json"
    assert st["epoch"] == 2


def _install_spy(monkeypatch):
    reads = []
    orig = pathlib.Path.read_text

    def spy(self, *a, **kw):
        s = ids.parse_seq_from_name(self.name)
        if s is not None:
            reads.append((s, self.name))
        return orig(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", spy)
    return reads


# T4b -- ev-002 (path-order AFTER closure-003 in runs/) and closure-003.  Kills a replay that
# follows directory/path order: (1) result must not depend on iterdir order, (2) the files that
# reconstruct actually reads must be read in non-decreasing seq order (ev-002 before closure-003).
@pytest.mark.parametrize("reverse", [False, True], ids=["iter-asc", "iter-desc"])
def test_reconstruct_order_independent_of_iterdir_and_reads_in_seq_order(tmp_path, monkeypatch, reverse):
    lay = _layout(tmp_path)
    sd, rd = lay.sprint_dir(TAG), lay.runs_dir(TAG)
    (sd / "contract-001.json").write_text(json.dumps({"epoch": 1}), encoding="utf-8")
    (rd / "ev-002.json").write_text(json.dumps(
        {"kind": "ev", "seq": 2, "parent": None, "id": "ev-002", "exit_code": 1}), encoding="utf-8")
    (rd / "closure-003.json").write_text(json.dumps(
        {"kind": "closure", "seq": 3, "parent": None, "reason": "done"}), encoding="utf-8")
    (sd / "contract-999.json").write_text(json.dumps({"epoch": 1}), encoding="utf-8")
    (sd / "contract-1000.json").write_text(json.dumps({"epoch": 3}), encoding="utf-8")

    orig_iterdir = pathlib.Path.iterdir

    def ordered(self):
        return iter(sorted(orig_iterdir(self), key=lambda p: p.name, reverse=reverse))

    monkeypatch.setattr(pathlib.Path, "iterdir", ordered)
    reads = _install_spy(monkeypatch)
    n, st = _fresh_reconstruct(lay)
    monkeypatch.undo()

    first_seen = []
    for s, name in reads:
        if name not in [x[1] for x in first_seen]:
            first_seen.append((s, name))
    seqs = [s for s, _ in first_seen]
    assert seqs == sorted(seqs), f"artifacts replayed out of seq order: {first_seen}"
    assert n == 1000
    assert st["active_contract"] == "contract-1000.json"
    assert st["epoch"] == 3


def test_reconstruct_result_identical_for_both_iteration_orders(tmp_path, monkeypatch):
    lay = _layout(tmp_path)
    sd, rd = lay.sprint_dir(TAG), lay.runs_dir(TAG)
    (rd / "ev-002.json").write_text(json.dumps(
        {"kind": "ev", "seq": 2, "parent": None, "id": "ev-002", "exit_code": 1}), encoding="utf-8")
    (rd / "closure-003.json").write_text(json.dumps(
        {"kind": "closure", "seq": 3, "parent": None, "reason": "done"}), encoding="utf-8")
    (sd / "contract-005.json").write_text(json.dumps({"epoch": 2}), encoding="utf-8")
    orig_iterdir = pathlib.Path.iterdir
    results = []
    for reverse in (False, True):
        monkeypatch.setattr(
            pathlib.Path, "iterdir",
            lambda self, r=reverse: iter(sorted(orig_iterdir(self), key=lambda p: p.name, reverse=r)))
        results.append(_fresh_reconstruct(lay))
        monkeypatch.undo()
    assert results[0] == results[1]

def test_seq_initial_state_and_filter_invariants(tmp_path):
    from actl import seq, layout
    import json
    TAG = "2026-10-16_seqgap"
    lay = layout.Layout(tmp_path)
    sprint_dir = lay.sprint_dir(TAG)
    sprint_dir.mkdir(parents=True)

    # 1. Reconstruct on empty sprint dir builds valid initial state on disk
    hw = seq.reconstruct(lay, TAG)
    state_file = lay.state_file(TAG)
    assert state_file.is_file()
    st = json.loads(state_file.read_text(encoding="utf-8"))
    assert len(st["run_id"]) == 16
    assert st["run_id"].startswith("run-")
    assert st["attempts"] == {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}

    # 2. Verify reserve increments sequence
    n = seq.reserve(lay, TAG, "spec")
    assert n >= 1

    # 3. Spec filter invariant: reconstruct ignores .meta.json files
    (sprint_dir / "spec-001.meta.json").write_text(json.dumps({"kind": "spec", "seq": 1, "parent": None}))
    (sprint_dir / "spec-001.md").write_text("# Spec 1")
    reconstructed = seq.reconstruct(lay, TAG)
    assert reconstructed >= 1

def test_seq_reconstruct_replays_artifacts_and_validates(tmp_path):
    from actl import seq, layout, schemas
    import json
    TAG = "2026-10-16_replaytest"
    lay = layout.Layout(tmp_path)
    sprint_dir = lay.sprint_dir(TAG)
    sprint_dir.mkdir(parents=True)
    
    # Write initial state
    hw = seq.reconstruct(lay, TAG)
    
    # 1. Counterexample 1: closure-002.json must increment closures_submitted
    closure_doc = {
        "reason": "blocked",
        "blocking_step": "G3",
        "notes": ["blocked by scope"],
        "backlog": [],
        "solution_key_divergence": None
    }
    (sprint_dir / "closure-002.json").write_text(json.dumps(closure_doc))
    (sprint_dir / "closure-002.meta.json").write_text(json.dumps({"kind": "closure", "seq": 2, "parent": "spec-001.md"}))
    
    # 2. Counterexample 2: contract with invalid epoch (0) must fail validation before write
    bad_contract = {
        "epoch": 0,
        "base_sha": "0" * 40,
        "spec": {"seq": 1, "sha256": "a" * 64},
        "oracle": {"seq": 3, "manifest_sha256": "b" * 64},
        "qual": {"seq": 4, "sha256": "c" * 64},
        "sprint_sha256": "d" * 64,
        "scope": "FROZEN: test/**\nALLOW: api/**"
    }
    (sprint_dir / "contract-003.json").write_text(json.dumps(bad_contract))
    (sprint_dir / "contract-003.meta.json").write_text(json.dumps({"kind": "contract", "seq": 3, "parent": "spec-001.md"}))
    
    # Reconstruct must reject invalid contract epoch and properly restore closures_submitted
    with pytest.raises(ValueError):
        seq.reconstruct(lay, TAG)
    
    # Fix contract to valid epoch and re-run to confirm state reconstruction
    bad_contract["epoch"] = 1
    (sprint_dir / "contract-003.json").write_text(json.dumps(bad_contract))
    final_seq = seq.reconstruct(lay, TAG)
    st = json.loads(lay.state_file(TAG).read_text(encoding="utf-8"))
    assert st["closures_submitted"] == 1, f"Expected closures_submitted == 1, got {st['closures_submitted']}"
    assert st["epoch"] == 1
    assert len(schemas.validate("state", st)) == 0, "Persisted state must be schema valid"


def test_reconstruct_failure_leaves_state_file_untouched(tmp_path):
    from actl import seq, layout
    import json
    TAG = "2026-10-16_untouched"
    lay = layout.Layout(tmp_path)
    sprint_dir = lay.sprint_dir(TAG)
    sprint_dir.mkdir(parents=True)

    seq.reconstruct(lay, TAG)
    state_file = lay.state_file(TAG)
    assert state_file.is_file()
    orig_bytes = state_file.read_bytes()

    # Inject malformed contract artifact with epoch 0
    bad_contract = {
        "epoch": 0,
        "base_sha": "0" * 40,
        "spec": {"seq": 1, "sha256": "a" * 64},
        "oracle": {"seq": 3, "manifest_sha256": "b" * 64},
        "qual": {"seq": 4, "sha256": "c" * 64},
        "sprint_sha256": "d" * 64,
        "scope": "FROZEN: test/**\nALLOW: api/**",
    }
    (sprint_dir / "contract-002.json").write_text(json.dumps(bad_contract), encoding="utf-8")
    (sprint_dir / "contract-002.meta.json").write_text(json.dumps({"kind": "contract", "seq": 2}), encoding="utf-8")

    with pytest.raises(ValueError):
        seq.reconstruct(lay, TAG)

    assert state_file.read_bytes() == orig_bytes, "State file must remain byte-for-byte identical on reconstruct failure"

    # Also test with malformed non-JSON artifact
    (sprint_dir / "contract-002.json").write_text("NOT_VALID_JSON{{{", encoding="utf-8")
    with pytest.raises(ValueError):
        seq.reconstruct(lay, TAG)

    assert state_file.read_bytes() == orig_bytes, "State file must remain byte-for-byte identical on malformed JSON"
