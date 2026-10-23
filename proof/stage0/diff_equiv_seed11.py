#!/usr/bin/env python3
# Authored-by: Perplexity (underlying model undisclosed). Differential runs for equivalent-claimed survivors. NOT EXECUTED.
# Usage: ACTL_REPO=$PWD python3 proof/stage0/diff_equiv_seed11.py   (exit 0 = no divergence, 1 = divergence)
import copy
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

REPO = Path(os.environ.get("ACTL_REPO") or Path(__file__).resolve().parents[1]).resolve()
sys.path.insert(0, str(REPO / "src"))
from actl import layout as L, schemas  # noqa: E402

TAG = "2026-10-16_diff-demo"


def mutant(relpath, lineno, old, new, modname):
    p = REPO / relpath
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    assert old in lines[lineno - 1], (relpath, lineno, old, lines[lineno - 1])
    lines[lineno - 1] = lines[lineno - 1].replace(old, new, 1)
    m = types.ModuleType(modname)
    m.__file__, m.__package__ = str(p), "actl"
    exec(compile("".join(lines), str(p), "exec"), m.__dict__)
    return m


def qual_fixture():
    base = REPO / "fixtures" / "golden" / "artifacts"
    for p in sorted(base.rglob("*.json")):
        if "invalid" in p.relative_to(base).parts:
            continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and d.get("kind") == "qual" and not schemas.validate("qual", d):
            return d
    sys.exit("no qual fixture")


QUAL = qual_fixture()


def build(root, rnd):
    lay = L.Layout(root)
    lay.ensure_sprint_tree(TAG)
    sd, rd = lay.sprint_dir(TAG), lay.runs_dir(TAG)
    for n in range(1, rnd.randint(1, 9)):
        k = rnd.choice(["spec", "sk", "od", "o", "contract", "closure", "ev", "esc", "live", "qual"])
        if k == "spec":
            (sd / f"spec-{n:03d}.md").write_text("s")
        elif k == "sk":
            (sd / f"solution_key-{n:03d}.patch").write_text("p")
        elif k == "od":
            (sd / f"oracle-draft-{n:03d}").mkdir()
        elif k == "o":
            (sd / f"oracle-{n:03d}").mkdir()
        elif k == "contract":
            (sd / f"contract-{n:03d}.json").write_text(json.dumps({"epoch": rnd.randint(1, 3)}))
        elif k == "closure":
            (rd / f"closure-{n:03d}.json").write_text(json.dumps({"kind": "closure", "seq": n, "parent": None, "reason": "done"}))
        elif k == "ev":
            (rd / f"ev-{n:03d}.json").write_text(json.dumps({"stage": rnd.choice(["guards", "live", None]), "hard_cap": rnd.random() < .4}))
        elif k in ("esc", "live"):
            res = {"action": rnd.choice(["grant_attempts", "waive_mutant", None]),
                   "count": rnd.choice([1, 2, "x", None]), "attempts_granted": rnd.choice([None, 3])}
            res = {a: b for a, b in res.items() if b is not None}
            name = f"escalation-{n:03d}.json" if k == "esc" else f"live-decision-{n:03d}.json"
            (rd / name).write_text(json.dumps({"stage": rnd.choice(["oracle", "implementer", "live", "curator", "bogus", None]) or "implementer", "resolution": res}))
        else:
            d = copy.deepcopy(QUAL)
            d["seq"], d["id"] = n, f"qual-{n:03d}"
            (rd / f"qual-{n:03d}.json").write_text(json.dumps(d))
    return lay


def outcome(mod, root):
    lay = L.Layout(root)
    try:
        r = mod.reconstruct(lay, TAG)
        return r, lay.state_file(TAG).read_bytes()
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, None


def diff_seq():
    from actl import seq as orig
    muts = [("299 get default", 299, '"oracle", 0', '"oracle", 1'),
            ("338 grants fallback", 338, '"oracle": 0', '"oracle": 1'),
            ("348 grants default", 348, ".get(stg, 0)", ".get(stg, 1)"),
            ("280 first-and (A or (B and C))", 280, " and ", " or ")]
    bad = 0
    for label, ln, old, new in muts:
        m = mutant("src/actl/seq.py", ln, old, new, "actl._mut_seq")
        for i in range(300):
            rnd = random.Random(i)
            tmp = Path(tempfile.mkdtemp())
            try:
                build(tmp / "base", rnd)
                if rnd.random() < .5:
                    orig.reconstruct(L.Layout(tmp / "base"), TAG)
                shutil.copytree(tmp / "base", tmp / "a")
                shutil.copytree(tmp / "base", tmp / "b")
                if outcome(orig, tmp / "a") != outcome(m, tmp / "b"):
                    print(f"DIVERGE {label} trial {i}")
                    bad += 1
                    break
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"equivalent over 300 trials: {label}")
    return bad
def diff_hashing42():
    rnd = random.Random(1)
    al = list("ab-.0Z_")
    for _ in range(200000):
        rels = {"".join(rnd.choice(al) for _ in range(rnd.randint(1, 6))).strip("/").encode() for _ in range(rnd.randint(2, 6))}
        rels = [r for r in rels if r]
        rows = [(r, r + b"\0" + b"-" + b"\0" + b"d" * 64 + b"\n") for r in rels]
        if sorted(rows, key=lambda t: t[0]) != sorted(rows, key=lambda t: t[1]):
            print("DIVERGE hashing:42", rels)
            return 1
    print("equivalent over 200000 trials: hashing:42")
    return 0
if __name__ == "__main__":
    total_failures = diff_seq() + diff_hashing42()
    sys.exit(1 if total_failures else 0)
