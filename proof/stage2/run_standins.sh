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

def clean():
    for m in mods: (src / f"{m}.py").unlink(missing_ok=True)
    if nr.exists(): shutil.rmtree(nr, ignore_errors=True)
    subprocess.run(["git", "checkout", "--", "src/actl"], check=True)

def populate(mode):
    clean()
    nr.mkdir(parents=True, exist_ok=True)
    (nr / "__init__.py").write_text("", encoding="utf-8")
    if mode == "empty":
        for m in mods: (src / f"{m}.py").write_text("", encoding="utf-8")
        (nr / "phase12.py").write_text("", encoding="utf-8")
    elif mode == "pass":
        for m in ["cmd_bundle", "cmd_unpack", "cmd_replay", "cmd_promote"]:
            c = m.replace("cmd_", "")
            (src / f"{m}.py").write_text(
                f'def register(sp): p=sp.add_parser("{c}"); p.set_defaults(func=lambda *a,**k: print("{{}}") or 0)\n',
                encoding="utf-8"
            )
        (src / "turns.py").write_text(
            'def allocate_turn(l,t,r): return (1, l.turns_dir(t)/f"{r}-1")\n'
            'def latest_turn(l,t,r): return (1, l.turns_dir(t)/f"{r}-1")\n'
            'def resolve_turn(l,t,i): return l.turns_dir(t)/i\n',
            encoding="utf-8"
        )
        (src / "bundle.py").write_text('def bundle_turn(*a,**k): return {}\n', encoding="utf-8")
        (src / "envelope.py").write_text('def parse_envelope(t): return []\ndef normalize_response(t): return t\n', encoding="utf-8")
        (src / "unpack.py").write_text('def unpack_response(*a,**k): return {"ok":True,"errors":[],"outputs":[]}\n', encoding="utf-8")
        (src / "patchsynth.py").write_text('def synthesize_patch(*a,**k): return ""\n', encoding="utf-8")
        (src / "repair.py").write_text('def generate_repair_prompt(*a,**k): return ""\n', encoding="utf-8")
        (src / "replay.py").write_text('def replay_turn(*a,**k): return {"turn_id":"a-1","match":True,"stored_ok":True,"replayed_ok":True,"diffs":[]}\n', encoding="utf-8")
        (src / "promote.py").write_text('def promote_role(l,t,r): return {"sprint_tag":t,"role":r,"promoted":[],"staged_to":"","active_spec":None,"active_solution_key":None,"active_oracle_draft":None}\n', encoding="utf-8")
        (nr / "phase12.py").write_text('PRIORITY=10\ndef evaluate(l,t,p=None): return {"action":"d","command":"d"}\n', encoding="utf-8")
    elif mode == "fail":
        for m in ["cmd_bundle", "cmd_unpack", "cmd_replay", "cmd_promote"]:
            c = m.replace("cmd_", "")
            (src / f"{m}.py").write_text(
                f'def register(sp): p=sp.add_parser("{c}"); p.set_defaults(func=lambda *a,**k: 1)\n',
                encoding="utf-8"
            )
        for m in ["turns","bundle","envelope","unpack","patchsynth","repair","replay","promote"]:
            (src / f"{m}.py").write_text('def __getattr__(n): raise RuntimeError("fail")\n', encoding="utf-8")
        (nr / "phase12.py").write_text('PRIORITY=10\ndef evaluate(*a,**k): raise RuntimeError("fail")\n', encoding="utf-8")

results = {"empty": {}, "pass": {}, "fail": {}}
try:
    for mode in ("empty", "pass", "fail"):
        populate(mode)
        print(f"\nEvaluating stand-in mode: {mode.upper()}", flush=True)
        for i in range(1, 18):
            p = f"P-S2-{i:02d}"
            print(f"  [{mode}] {p}...", end="", flush=True)
            res = subprocess.run(["bash", f"proof/stage2/{p}.sh"], capture_output=True, text=True)
            out = res.stdout + res.stderr
            rc = res.returncode
            is_imp = any(s in out for s in ["E   ImportError:", "E   ModuleNotFoundError:"])
            is_setup = any(s in out for s in ["FixtureLookupError", "ERROR at setup", "setup failure"])
            is_assert = any(s in out for s in ["AssertionError", "FAILED ", "FAIL:"])
            if rc == 0: cls = "PASS"
            elif rc == 4 or "ENVFAIL" in out or "environment error" in out.lower(): cls = "ENV"
            elif is_imp: cls = "IMPORT"
            elif is_setup: cls = "SETUP"
            elif is_assert: cls = "ASSERT"
            else: cls = "OTHER"
            results[mode][p] = cls
            print(f" -> {cls}", flush=True)
finally:
    clean()

counts = {m: {k: list(results[m].values()).count(k) for k in ["PASS","ENV","IMPORT","SETUP","ASSERT","OTHER"]} for m in results}
print("\n=== STAND-IN SUMMARY ===")
for m, c in counts.items():
    print(f"{m.upper():5s} -> ASSERT:{c['ASSERT']:2d} | IMPORT:{c['IMPORT']:2d} | PASS:{c['PASS']:2d} | SETUP:{c['SETUP']:2d} | ENV:{c['ENV']:2d} | OTHER:{c['OTHER']:2d}")
assert counts["empty"]["PASS"] == 0 and counts["empty"]["OTHER"] == 0
assert counts["empty"]["IMPORT"] + counts["empty"]["ASSERT"] == 17
for m in ("pass", "fail"):
    assert counts[m]["ASSERT"] == 17 and counts[m]["OTHER"] == 0 and counts[m]["PASS"] == 0 and counts[m]["IMPORT"] == 0
print("OK: run_standins verified")
