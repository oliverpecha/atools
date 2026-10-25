# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from actl import schemas, seq  # noqa: E402
from actl.layout import Layout  # noqa: E402

TAG = "2026-10-16_gap2-recon"
ZERO = {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}
STAGES = ("oracle", "implementer", "live", "curator")


def z(**kw):
    d = dict(ZERO)
    d.update(kw)
    return d


def mk(tmp_path):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    return lay


def st(lay):
    return json.loads(lay.state_file(TAG).read_text(encoding="utf-8"))


def put(lay, name, obj, where="sprint"):
    d = lay.sprint_dir(TAG) if where == "sprint" else lay.runs_dir(TAG)
    (d / name).write_text(json.dumps(obj), encoding="utf-8")


def recon(lay):
    top = seq.reconstruct(lay, TAG)
    return top, st(lay)


def qual_doc(n):
    base = REPO / "fixtures" / "golden" / "artifacts"
    for p in sorted(base.rglob("*.json")):
        if "invalid" in p.relative_to(base).parts:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("kind") == "qualification":
            d = copy.deepcopy(d)
            d["seq"] = n
            d["id"] = f"qualification-{n:03d}"
            return d
    pytest.fail("FAIL: no valid qual fixture under fixtures/golden/artifacts (adjust qual_doc)", pytrace=False)


def assert_state_valid(s):
    assert schemas.validate("state", s) == []


# ---------- defaults ----------

def test_defaults_when_state_json_absent(tmp_path):
    lay = mk(tmp_path)
    assert not lay.state_file(TAG).exists()
    top, s = recon(lay)
    assert top == 0
    assert s["run_id"] == "run-" + hashlib.sha256(TAG.encode()).hexdigest()[:12]
    assert s["sprint_tag"] == TAG
    assert s["seq"] == 0 and s["epoch"] == 1 and s["status"] == "draft"
    for k in ("active_stage", "active_spec", "active_solution_key", "active_oracle_draft",
              "active_oracle", "active_contract"):
        assert s[k] is None, k
    assert s["attempts"] == ZERO and s["grants"] == ZERO
    assert s["closures_submitted"] == 0 and s["hard_caps_tripped"] == 0
    assert s["tmux_sessions"] == []
    assert_state_valid(s)


def test_defaults_rebuilt_after_deleting_state_with_artifacts_present(tmp_path):
    lay = mk(tmp_path)
    put(lay, "contract-005.json", {"epoch": 2})
    put(lay, "verification-006.json", {"stage": "guards"})
    seq.reconstruct(lay, TAG)
    lay.state_file(TAG).unlink()
    top, s = recon(lay)
    assert top == 6 and s["seq"] == 6
    assert s["epoch"] == 2 and s["attempts"] == z(implementer=1)
    assert s["grants"] == ZERO
    assert_state_valid(s)


def test_existing_valid_state_is_reset_not_carried(tmp_path):
    lay = mk(tmp_path)
    seq.reconstruct(lay, TAG)
    seq.update_state(lay, TAG, {
        "attempts": {"oracle": 5, "implementer": 4, "live": 3, "curator": 2},
        "grants": {"oracle": 1, "implementer": 2, "live": 3, "curator": 4},
        "closures_submitted": 4, "hard_caps_tripped": 2, "epoch": 2, "status": "running",
        "active_stage": "oracle", "active_spec": "spec-009.md",
        "active_solution_key": "solution_key-009.patch", "active_oracle_draft": "oracle-draft-009",
        "active_oracle": "oracle-009", "active_contract": "contract-009.json",
    })
    top, s = recon(lay)
    assert top == 0 and s["seq"] == 0
    assert s["epoch"] == 1 and s["status"] == "draft"
    for k in ("active_stage", "active_spec", "active_solution_key", "active_oracle_draft",
              "active_oracle", "active_contract"):
        assert s[k] is None, k
    assert s["attempts"] == ZERO and s["grants"] == ZERO
    assert s["closures_submitted"] == 0 and s["hard_caps_tripped"] == 0
    assert_state_valid(s)


# ---------- per kind counters, N = 1, 2, 3 ----------

@pytest.mark.parametrize("n", [1, 2, 3])
def test_qual_counts_attempts_oracle(tmp_path, n):
    lay = mk(tmp_path)
    for i in range(n):
        put(lay, f"qualification-{i + 4:03d}.json", qual_doc(i + 4))
    top, s = recon(lay)
    assert top == n + 3 and s["seq"] == n + 3
    assert s["attempts"] == z(oracle=n)
    assert s["grants"] == ZERO and s["closures_submitted"] == 0 and s["hard_caps_tripped"] == 0
    assert s["epoch"] == 1 and s["status"] == "draft" and s["active_contract"] is None
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
@pytest.mark.parametrize("stage,key", [("guards", "implementer"), ("offline", "implementer"),
                                       ("blocked_check", "implementer"), ("live", "live"),
                                       (None, "implementer")])
def test_ev_counts_attempts(tmp_path, n, stage, key):
    lay = mk(tmp_path)
    for i in range(n):
        doc = {"kind": "verification", "seq": i + 1, "parent": None}
        if stage is not None:
            doc["stage"] = stage
        put(lay, f"verification-{i + 1:03d}.json", doc, "runs")
    top, s = recon(lay)
    assert top == n
    assert s["attempts"] == z(**{key: n})
    assert s["grants"] == ZERO and s["hard_caps_tripped"] == 0 and s["closures_submitted"] == 0
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_hard_caps_tripped_counts_each_qualifying_ev_once(tmp_path, n):
    lay = mk(tmp_path)
    seqn = 0
    for i in range(n):
        seqn += 1
        if i % 2 == 0:
            put(lay, f"verification-{seqn:03d}.json", {"hard_cap": True}, "runs")
        else:
            put(lay, f"verification-{seqn:03d}.json", {"session": {"hard_cap": True}}, "runs")
    seqn += 1
    put(lay, f"verification-{seqn:03d}.json", {"hard_cap": True, "session": {"hard_cap": True}}, "runs")
    for extra in ({"hard_cap": False}, {"session": {"hard_cap": False}}, {"session": "x"}, {}):
        seqn += 1
        put(lay, f"verification-{seqn:03d}.json", extra, "runs")
    top, s = recon(lay)
    assert s["hard_caps_tripped"] == n + 1
    assert s["attempts"] == z(implementer=seqn)
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_closures_submitted_counts(tmp_path, n):
    lay = mk(tmp_path)
    for i in range(n):
        put(lay, f"closure-{i + 1:03d}.json",
            {
                "kind": "closure",
                "seq": i + 1,
                "parent": None,
                "reason": "done",
                "blocking_step": None,
                "notes": [],
                "backlog": [],
                "solution_key_divergence": None,
            }, "sprint")
    top, s = recon(lay)
    assert top == n and s["closures_submitted"] == n
    assert s["attempts"] == ZERO and s["status"] == "draft"
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_contracts_set_active_epoch_and_status(tmp_path, n):
    lay = mk(tmp_path)
    for i in range(n):
        put(lay, f"contract-{i + 5:03d}.json", {"epoch": i + 1})
    top, s = recon(lay)
    assert top == n + 4
    assert s["active_contract"] == f"contract-{n + 4:03d}.json"
    assert s["epoch"] == n
    assert s["status"] == "running" and s["active_stage"] == "implementer"
    assert s["attempts"] == ZERO and s["grants"] == ZERO
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
@pytest.mark.parametrize("stage", STAGES)
def test_escalation_grants_per_stage(tmp_path, n, stage):
    lay = mk(tmp_path)
    for i in range(n):
        put(lay, f"escalation-{i + 1:03d}.json",
            {"stage": stage, "resolution": {"action": "grant_attempts", "count": 2}}, "runs")
    top, s = recon(lay)
    assert top == n
    assert s["grants"] == z(**{stage: 2 * n})
    assert s["attempts"] == ZERO
    assert_state_valid(s)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_escalation_default_stage_and_default_count(tmp_path, n):
    lay = mk(tmp_path)
    for i in range(n):
        put(lay, f"escalation-{i + 1:03d}.json", {"resolution": {"action": "grant_attempts"}}, "runs")
    _, s = recon(lay)
    assert s["grants"] == z(implementer=n)


def test_escalation_grant_key_count_precedence_and_attempts_granted(tmp_path):
    lay = mk(tmp_path)
    put(lay, "escalation-001.json", {"stage": "oracle", "resolution": {"action": "grant_attempts", "grant": 4}}, "runs")
    put(lay, "escalation-002.json",
        {"stage": "oracle", "resolution": {"action": "grant_attempts", "grant": 4, "count": 1}}, "runs")
    put(lay, "escalation-003.json", {"stage": "live", "resolution": {"attempts_granted": 3}}, "runs")
    _, s = recon(lay)
    assert s["grants"] == z(oracle=5, live=3)


def test_escalation_unknown_stage_and_bad_count_ignored(tmp_path):
    lay = mk(tmp_path)
    put(lay, "escalation-001.json", {"stage": "bogus", "resolution": {"action": "grant_attempts", "count": 5}}, "runs")
    put(lay, "escalation-002.json", {"stage": "live", "resolution": {"action": "grant_attempts", "count": "2"}}, "runs")
    put(lay, "escalation-003.json", {"stage": "bogus", "resolution": {"attempts_granted": 7}}, "runs")
    _, s = recon(lay)
    assert s["grants"] == ZERO
    assert_state_valid(s)


def test_halt_ev_sets_hold_then_grant_resolves_to_running(tmp_path):
    lay = mk(tmp_path)
    put(lay, "verification-001.json", {"halt": "integrity_mismatch"}, "runs")
    _, s = recon(lay)
    assert s["status"] == "hold"
    put(lay, "escalation-002.json", {"stage": "implementer", "resolution": {"action": "grant_attempts"}}, "runs")
    _, s = recon(lay)
    assert s["status"] == "running" and s["grants"] == z(implementer=1)


# ---------- artifact pointers and decoys ----------

def test_each_kind_sets_only_its_own_pointer(tmp_path):
    lay = mk(tmp_path)
    put(lay, "spec-001.md", None) if False else (lay.sprint_dir(TAG) / "spec-001.md").write_text("s")
    (lay.sprint_dir(TAG) / "solution_key-002.patch").write_text("p")
    (lay.sprint_dir(TAG) / "oracle-draft-003").mkdir()
    (lay.sprint_dir(TAG) / "oracle-004").mkdir()
    put(lay, "contract-005.json", {"epoch": 1})
    top, s = recon(lay)
    assert top == 5
    assert s["active_spec"] == "spec-001.md"
    assert s["active_solution_key"] == "solution_key-002.patch"
    assert s["active_oracle_draft"] == "oracle-draft-003"
    assert s["active_oracle"] == "oracle-004"
    assert s["active_contract"] == "contract-005.json"
    assert_state_valid(s)


def test_decoys_are_ignored(tmp_path):
    lay = mk(tmp_path)
    grant = {"stage": "live", "resolution": {"action": "grant_attempts", "count": 9}}
    (lay.sprint_dir(TAG) / "spec-001.md").write_text("s")
    put(lay, "spec-001.md.meta.json", {"kind": "spec", "seq": 1, "parent": None, "sha256": "0" * 64})
    put(lay, "escalation-001.json", {"stage": "oracle", "resolution": {"action": "grant_attempts", "count": 2}}, "runs")
    put(lay, "escalation-001.meta.json", grant, "runs")
    put(lay, "escalation-001.json.bak", grant, "runs")
    put(lay, "xescalation-002.json", grant, "runs")
    put(lay, "qualification-004.json", qual_doc(4), "runs")
    top, s = recon(lay)
    assert top == 4
    assert s["active_spec"] == "spec-001.md"
    assert s["attempts"] == z(oracle=1)
    assert s["grants"] == z(oracle=2)
    assert s["closures_submitted"] == 0 and s["hard_caps_tripped"] == 0
    assert_state_valid(s)


def test_ev_live_decision_and_implementer_dir_not_taken_as_escalation(tmp_path):
    lay = mk(tmp_path)
    put(lay, "verification-002.json", {"stage": "guards", "resolution": {"action": "grant_attempts", "count": 9}}, "runs")
    put(lay, "live-decision-003.json", {"stage": "live", "resolution": {"action": "grant_attempts", "count": 5}}, "runs")
    (lay.runs_dir(TAG) / "implementer-004").mkdir()
    top, s = recon(lay)
    assert top == 4
    assert s["grants"] == ZERO
    assert s["attempts"] == z(implementer=1)
    assert_state_valid(s)


# ---------- status truth table (frozen/draft) ----------

@pytest.mark.parametrize("toml_text,want", [
    (None, "draft"),
    ('status = "draft"\n', "draft"),
    ('status = "frozen"\n', "running"),
    ("status = [\n", "draft"),
])
@pytest.mark.parametrize("prior", ["draft", "running", "hold", "done"])
def test_frozen_draft_truth_table(tmp_path, toml_text, want, prior):
    lay = mk(tmp_path)
    seq.reconstruct(lay, TAG)
    seq.update_state(lay, TAG, {"status": prior})
    if toml_text is not None:
        lay.sprint_toml(TAG).write_text(toml_text, encoding="utf-8")
    _, s = recon(lay)
    assert s["status"] == want
    assert_state_valid(s)


# ---------- idempotence, seq sources, reserve continuation ----------

def test_reconstruct_idempotent_and_reserve_continues(tmp_path):
    lay = mk(tmp_path)
    (lay.sprint_dir(TAG) / "spec-001.md").write_text("s")
    put(lay, "contract-002.json", {"epoch": 2})
    put(lay, "qualification-003.json", qual_doc(3), "runs")
    put(lay, "verification-004.json", {"stage": "live", "hard_cap": True}, "runs")
    put(lay, "escalation-005.json", {"stage": "curator", "resolution": {"action": "grant_attempts"}}, "runs")
    put(lay, "closure-006.json", {"kind": "closure", "seq": 6, "parent": None, "reason": "done"}, "runs")
    r1, s1 = recon(lay)
    b1 = lay.state_file(TAG).read_bytes()
    hw1 = (lay.runs_dir(TAG) / "seq.highwater").read_bytes()
    r2, s2 = recon(lay)
    assert (r1, s1) == (r2, s2)
    assert lay.state_file(TAG).read_bytes() == b1
    assert (lay.runs_dir(TAG) / "seq.highwater").read_bytes() == hw1 == b"6\n"
    assert seq.reserve(lay, TAG, "verification") == 7


def test_max_seq_sources(tmp_path):
    lay = mk(tmp_path)
    (lay.runs_dir(TAG) / "seq.highwater").write_text("7\n")
    put(lay, "verification-004.json", {"stage": "guards"}, "runs")
    assert seq.reconstruct(lay, TAG) == 7
    (lay.outbox(TAG, "architect") / "spec-009.md").write_text("s")
    assert seq.reconstruct(lay, TAG) == 9
    ws = lay.workspace("implementer-012", TAG)
    ws.mkdir(parents=True)
    top, s = recon(lay)
    assert top == 12 and s["seq"] == 12
    assert (lay.runs_dir(TAG) / "seq.highwater").read_text() == "12\n"


def test_garbage_highwater_ignored(tmp_path):
    lay = mk(tmp_path)
    (lay.runs_dir(TAG) / "seq.highwater").write_text("abc\n")
    assert seq.reconstruct(lay, TAG) == 0
