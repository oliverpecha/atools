# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-06 / S0-R5: seq.reconstruct."""
import json

from helpers import *  # noqa


def _prep(tmp_path):
    root = tmp_path / "root"; install_golden(root)
    need("actl.seq"); need("actl.layout")
    from actl.layout import Layout
    lay = Layout(root)
    ev = json.loads((GOLDEN / "artifacts" / "valid" / "ev" / "ev_base.json").read_text())
    (lay.runs_dir(TAG) / "ev-007.json").write_text(json.dumps(ev))
    clo = json.loads((GOLDEN / "artifacts" / "valid" / "closure" / "closure_stamped.json").read_text())
    lay.outbox(TAG, "implementer").mkdir(parents=True, exist_ok=True)
    (lay.outbox(TAG, "implementer") / "closure-006.json").write_text(json.dumps(clo))
    return root, lay


def test_reconstruct_after_deleting_state_equals_highest_seq(tmp_path):
    root, lay = _prep(tmp_path)
    from actl import seq
    lay.state_file(TAG).unlink()
    got = seq.reconstruct(lay, TAG)
    if got != 7: fail("highest artifact seq is 7 (ev-007.json), reconstruct returned %r" % got)
    st = json.loads(lay.state_file(TAG).read_text())
    if st["seq"] != 7: fail("rebuilt state.json seq must be 7, got %s" % st["seq"])
    if st.get("active_contract") != "contract-005.json": fail("active_contract not restored from contract-005.json: %r" % st.get("active_contract"))
    if st.get("epoch") != 1: fail("epoch not restored")
    if st.get("sprint_tag") != TAG: fail("sprint_tag not restored")
    errs = need_attr(need("actl.schemas"), "validate")("state", st)
    if errs: fail("reconstructed state.json is not schema-valid: %s" % errs)
    if seq.reconstruct(lay, TAG) != 7: fail("reconstruct must be idempotent")


def test_workspace_and_highwater_participate(tmp_path):
    root, lay = _prep(tmp_path)
    from actl import seq
    (root / "workspaces" / TAG / "implementer-009").mkdir(parents=True)
    lay.state_file(TAG).unlink()
    if seq.reconstruct(lay, TAG) != 9: fail("sprint-scoped workspaces/{tag}/implementer-009 must count (expected 9)")
    (lay.runs_dir(TAG) / "seq.highwater").write_text("12\n")
    if seq.reconstruct(lay, TAG) != 12: fail("seq = max(highwater, artifacts) expected 12")
    n = seq.reserve(lay, TAG, "ev")
    if n != 13: fail("reserve after reconstruct must continue at 13, got %s" % n)


def test_handoff_two_levels_are_scanned(tmp_path):
    root, lay = _prep(tmp_path)
    from actl import seq
    lay.inbox(TAG, "challenger").mkdir(parents=True, exist_ok=True)
    (lay.inbox(TAG, "challenger") / "solution_key-011.patch").write_text("x")
    lay.state_file(TAG).unlink()
    if seq.reconstruct(lay, TAG) != 11: fail("files two levels under handoff/{tag}/ must be scanned (expected 11)")
