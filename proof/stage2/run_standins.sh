#!/usr/bin/env bash
''''exec python3 "$0" "$@" # '''
import os, pathlib, shutil, subprocess, sys

wt = pathlib.Path.cwd()
src = wt / "src" / "actl"
nr = src / "next_rules"
mods = [
    "turns", "bundle", "envelope", "unpack", "patchsynth",
    "repair", "replay", "promote", "cmd_bundle", "cmd_unpack",
    "cmd_replay", "cmd_promote"
]

def classify(rc, out):
    # R4-03: hierarchy SETUP -> IMPORT -> OTHER(RuntimeError) -> ASSERT
    lines = out.splitlines()
    has_fail = any(s in out for s in ["FAIL:", "FAILED "])

    if rc == 0 and has_fail:
        return "OTHER"
    if rc == 0:
        return "PASS"
    if rc == 4 or "ENVFAIL" in out or "environment error" in out.lower():
        return "ENV"

    is_setup = any(
        "ERROR at setup of" in l
        or "FixtureLookupError" in l
        or "setup failure" in l.lower()
        or "setup error" in l.lower()
        or (l.startswith("ERROR:") and "setup" in l.lower())
        for l in lines
    )
    if is_setup:
        return "SETUP"

    is_imp = (
        any(l.startswith("E   ImportError:") for l in lines)
        or any(l.startswith("E   ModuleNotFoundError:") for l in lines)
        or any("No module named " in l for l in lines)
        or any("cannot import name " in l for l in lines)
    )
    if is_imp:
        return "IMPORT"

    # RuntimeError without AssertionError is OTHER (not ASSERT via FAILED summary)
    if "RuntimeError" in out and "AssertionError" not in out:
        return "OTHER"

    is_assert = (
        any(l.startswith("E   AssertionError") for l in lines)
        or any("pytest.fail" in l for l in lines)
        or any(l.startswith("FAILED ") for l in lines)
        or any(l.startswith("FAIL: ") for l in lines)
    )
    if is_assert:
        return "ASSERT"

    return "OTHER"

# Self-tests
assert classify(0, "All good\nFAIL: background error") == "OTHER"
assert classify(1, "FAIL: setup failure in harness") == "SETUP"
assert classify(1, "ERROR: setup hook failed") == "SETUP"
assert classify(1, "E   AssertionError: 1 != 2\nFAILED test.py::t") == "ASSERT"
assert classify(1, "E   RuntimeError: stand-in fail\nFAILED test.py::t") == "OTHER"
assert classify(1, "E   RuntimeError: x\nE   AssertionError: y\nFAILED test.py::t") == "ASSERT"

def clean():
    for m in mods:
        (src / f"{m}.py").unlink(missing_ok=True)
    if nr.exists():
        shutil.rmtree(nr, ignore_errors=True)
    subprocess.run(["git", "checkout", "--", "src/actl"], check=True)

def populate(mode):
    clean()
    nr.mkdir(parents=True, exist_ok=True)
    (nr / "__init__.py").write_text("", encoding="utf-8")
    if mode == "empty":
        for m in mods:
            (src / f"{m}.py").write_text("", encoding="utf-8")
        (nr / "phase12.py").write_text("", encoding="utf-8")
    elif mode == "pass":
        for m in ["cmd_bundle", "cmd_unpack", "cmd_replay", "cmd_promote"]:
            c = m.replace("cmd_", "")
            (src / f"{m}.py").write_text(
                f'def register(sp): p=sp.add_parser("{c}"); '
                f'p.set_defaults(func=lambda *a,**k: print("{{}}") or 0)\n',
                encoding="utf-8"
            )
        (src / "turns.py").write_text(
            'def allocate_turn(l,t,r): return (1, l.turns_dir(t)/f"{r}-1")\n'
            'def latest_turn(l,t,r): return (1, l.turns_dir(t)/f"{r}-1")\n'
            'def resolve_turn(l,t,i): return l.turns_dir(t)/i\n',
            encoding="utf-8"
        )
        (src / "bundle.py").write_text(
            'def bundle_turn(*a,**k): return {}\n', encoding="utf-8"
        )
        (src / "envelope.py").write_text(
            'def parse_envelope(t): return []\n'
            'def normalize_response(t): return t\n', encoding="utf-8"
        )
        (src / "unpack.py").write_text(
            'def unpack_response(*a,**k): return {"ok":True,"errors":[],"outputs":[]}\n',
            encoding="utf-8"
        )
        (src / "patchsynth.py").write_text(
            'def synthesize_patch(*a,**k): return ""\n', encoding="utf-8"
        )
        (src / "repair.py").write_text(
            'def generate_repair_prompt(*a,**k): return ""\n', encoding="utf-8"
        )
        (src / "replay.py").write_text(
            'def replay_turn(*a,**k): return {"turn_id":"a-1","match":True,'
            '"stored_ok":True,"replayed_ok":True,"diffs":[]}\n',
            encoding="utf-8"
        )
        (src / "promote.py").write_text(
            'def promote_role(l,t,r): return {"sprint_tag":t,"role":r,'
            '"promoted":[],"staged_to":"","active_spec":None,'
            '"active_solution_key":None,"active_oracle_draft":None}\n',
            encoding="utf-8"
        )
        (nr / "phase12.py").write_text(
            'PRIORITY=10\ndef evaluate(l,t,p=None): '
            'return {"action":"d","command":"d"}\n',
            encoding="utf-8"
        )
    elif mode == "fail":
        # R4-03: FAIL stand-in raises AssertionError so rejection is assertion-level
        for m in ["cmd_bundle", "cmd_unpack", "cmd_replay", "cmd_promote"]:
            c = m.replace("cmd_", "")
            (src / f"{m}.py").write_text(
                f'def register(sp): p=sp.add_parser("{c}"); '
                f'p.set_defaults(func=lambda *a,**k: (_ for _ in ()).throw(AssertionError("stand-in fail")))\n',
                encoding="utf-8"
            )
        for m in [
            "turns", "bundle", "envelope", "unpack", "patchsynth",
            "repair", "replay", "promote"
        ]:
            (src / f"{m}.py").write_text(
                'def __getattr__(n): raise AssertionError("stand-in fail")\n',
                encoding="utf-8"
            )
        (nr / "phase12.py").write_text(
            'PRIORITY=10\ndef evaluate(*a,**k): raise AssertionError("stand-in fail")\n',
            encoding="utf-8"
        )

results = {"empty": {}, "pass": {}, "fail": {}}
try:
    for mode in ("empty", "pass", "fail"):
        populate(mode)
        for i in range(1, 18):
            p = f"P-S2-{i:02d}"
            res = subprocess.run(
                ["bash", f"proof/stage2/{p}.sh"],
                capture_output=True, text=True
            )
            results[mode][p] = classify(res.returncode, res.stdout + res.stderr)
finally:
    clean()

counts = {
    m: {
        k: list(results[m].values()).count(k)
        for k in ["PASS", "ENV", "IMPORT", "SETUP", "ASSERT", "OTHER"]
    }
    for m in results
}

for m in ("empty", "pass", "fail"):
    c = counts[m]
    print(
        f"{m.upper():5s} -> ASSERT:{c['ASSERT']:2d} | IMPORT:{c['IMPORT']:2d} | "
        f"PASS:{c['PASS']:2d} | SETUP:{c['SETUP']:2d} | ENV:{c['ENV']:2d} | "
        f"OTHER:{c['OTHER']:2d}"
    )

expected_empty_import = {pn for pn, c in results["empty"].items() if c == "IMPORT"}
for pn in expected_empty_import:
    assert results["empty"][pn] == "IMPORT"
for pn in set(results["empty"]) - expected_empty_import:
    assert results["empty"][pn] == "ASSERT"

assert counts["empty"]["PASS"] == 0
assert counts["empty"]["SETUP"] == 0
assert counts["empty"]["ENV"] == 0
assert counts["empty"]["OTHER"] == 0
assert counts["empty"]["IMPORT"] == 3
assert counts["empty"]["ASSERT"] == 14

for m in ("pass", "fail"):
    assert counts[m]["ASSERT"] == 17
    assert counts[m]["PASS"] == 0
    assert counts[m]["IMPORT"] == 0
    assert counts[m]["SETUP"] == 0
    assert counts[m]["ENV"] == 0
    assert counts[m]["OTHER"] == 0

print(f"EMPTY_IMPORTS: {sorted(expected_empty_import)}")
print("OK: run_standins verified with strict classification")
