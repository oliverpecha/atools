#!/usr/bin/env python3
"""Token-level mutation review for Stage 0. Run from ~/atools with a clean, committed tree."""
import argparse, io, json, os, random, re, shutil, subprocess, sys, tokenize
from pathlib import Path

REPO = Path.cwd()
import tempfile
WORK = Path(os.environ.get("MUTATE_WORKDIR") or tempfile.gettempdir())
WT = WORK / "mut_wt"
REPORT = WORK / "mutation_report.json"
PYTEST = ["python3", "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"]
T = "test/actl/"
PY_TARGETS = {
    "src/actl/hashing.py": [T + "test_p07_hashing.py", T + "test_s0_gap_hashing.py"],
    "src/actl/ids.py": [T + "test_p04_sprint.py", T + "test_p05_seq.py", T + "test_p26_interfaces.py", T + "test_s0_gap_ids.py"],
    "src/actl/layout.py": [T + "test_p03_layout.py", T + "test_p04_sprint.py"],
    "src/actl/seq.py": [T + "test_p05_seq.py", T + "test_p06_reconstruct.py", T + "test_s0_gap_seq_reconstruct_order.py"],
    "src/actl/scope.py": [T + "test_p12_scope.py", T + "test_s0_gap_scope_globs.py"],
    "src/actl/schemas.py": [T + "test_p08_schemas.py", T + "test_p15_expected.py", T + "test_s0_gap_schemas_oneof.py", T + "test_s0_gap_conformance.py"],
    "src/actl/sprint.py": [T + "test_p04_sprint.py", T + "test_p09_defaults.py", T + "test_s0_gap_sprint_initial_state.py"],
    "src/actl/cli.py": [T + "test_p11_cli.py", T + "test_p14_registries.py", T + "test_s0_gap_cli_json_errors.py"],
    "src/actl/next.py": [T + "test_p13_next_rules.py", T + "test_p14_registries.py", T + "test_s0_gap_next_rule_signatures.py"],
}
JSON_TESTS = [T + "test_p08_schemas.py", T + "test_s0_gap_schemas_oneof.py"]
GAP = sorted(str(q) for q in Path("test/actl").glob("test_s0_gap*.py"))
for _k in PY_TARGETS:
    PY_TARGETS[_k] = PY_TARGETS[_k] + [g for g in GAP if g not in PY_TARGETS[_k]]
JSON_TESTS = JSON_TESTS + [g for g in GAP if g not in JSON_TESTS]
BASH_TARGETS = {"src/router/process.py": ["bash", "-c", "PYTHONPATH=src python3 -m pytest -x -q -p no:cacheprovider $(grep -l router.process test/actl/test_*.py) && bash proof/run_suite_exit_code.sh && bash proof/run_suite_session_persistence.sh"]}
SWAP_OP = {"==": "!=", "!=": "==", "<": "<=", "<=": "<", ">": ">=", ">=": ">"}
SWAP_NAME = {"and": "or", "or": "and", "True": "False", "False": "True", "not": ""}

def py_sites(src):
    sites = []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        (r, c), (er, ec) = t.start, t.end
        if r != er:
            continue
        s = t.string
        if t.type == tokenize.OP and s in SWAP_OP:
            new = SWAP_OP[s]
        elif t.type == tokenize.NAME and s in SWAP_NAME:
            new = SWAP_NAME[s]
        elif t.type == tokenize.NUMBER and re.fullmatch(r"\d+", s):
            new = str(int(s) + 1)
        elif t.type == tokenize.NUMBER and re.fullmatch(r"0o[0-7]+", s):
            new = "0o%o" % (int(s, 8) + 1)
        else:
            continue
        sites.append((r, c, ec, s, new))
    return sites

def apply_py(src, site):
    r, c, ec, old, new = site
    lines = src.splitlines(keepends=True)
    lines[r - 1] = lines[r - 1][:c] + new + lines[r - 1][ec:]
    return "".join(lines)

JSON_RULES = [
    (r'"additionalProperties":\s*false', lambda m: m.group(0)[:-5] + "true"),
    (r'"minimum":\s*[1-9]\d*', lambda m: re.sub(r"\d+$", lambda n: str(int(n.group(0)) - 1), m.group(0))),
    (r'"maximum":\s*\d+', lambda m: re.sub(r"\d+$", lambda n: str(int(n.group(0)) + 1), m.group(0))),
    (r'"maxLength":\s*\d+', lambda m: re.sub(r"\d+$", lambda n: str(int(n.group(0)) + 1), m.group(0))),
    (r'\\Z"', lambda m: '$"'),
]

def json_sites(text):
    return [(m.start(), m.end(), m.group(0), fn(m)) for rx, fn in JSON_RULES for m in re.finditer(rx, text)]

def sh(cmd, cwd, timeout):
    env = dict(os.environ, PYTHONPATH="src", PYTHONDONTWRITEBYTECODE="1")
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode
    except subprocess.TimeoutExpired:
        return 124

import ast
EXCLUDE_FUNCS = {"src/router/process.py": {"stream_session", "attach_session", "tail_logs", "print_sessions", "format_duration"}}

def in_excluded(src, rel, line):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name in EXCLUDE_FUNCS[rel] and n.lineno <= line <= n.end_lineno:
            return True
    return False

def setup():
    if subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout.strip():
        sys.exit("ERROR: working tree not clean; commit first")
    if WT.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(WT)], cwd=REPO)
        shutil.rmtree(WT, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=REPO)
    subprocess.run(["git", "worktree", "add", "--detach", str(WT), "HEAD"], cwd=REPO, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", default="20261020")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    setup()
    jobs = []
    for rel, tests in PY_TARGETS.items():
        jobs.append((rel, "py", PYTEST + tests))
    for rel, cmd in BASH_TARGETS.items():
        jobs.append((rel, "py", cmd))
    for p in sorted((WT / "schemas").glob("*.json")):
        jobs.append((str(p.relative_to(WT)), "json", PYTEST + JSON_TESTS))
    if a.only:
        jobs = [j for j in jobs if any(o in j[0] for o in a.only)]
    for cmd in {tuple(j[2]) for j in jobs}:
        rc = sh(list(cmd), WT, a.timeout * 2)
        if rc != 0:
            env = dict(os.environ, PYTHONPATH="src", PYTHONDONTWRITEBYTECODE="1")
            p_dbg = subprocess.run(list(cmd), cwd=WT, env=env, capture_output=True, text=True)
            print("=== CONTROL STDOUT ===")
            print(p_dbg.stdout)
            print("=== CONTROL STDERR ===")
            print(p_dbg.stderr)
            sys.exit(f"CONTROL FAILED (rc={rc}) for {' '.join(cmd)}; fix before mutating")
    print(f"controls green for {len({tuple(j[2]) for j in jobs})} commands")
    results = []
    try:
        for rel, kind, cmd in jobs:
            path = WT / rel
            orig = path.read_text(encoding="utf-8")
            sites = py_sites(orig) if kind == "py" else json_sites(orig)
            if kind == "py" and rel in EXCLUDE_FUNCS:
                sites = [s for s in sites if not in_excluded(orig, rel, s[0])]
            rng = random.Random(f"{a.seed}:{rel}")
            rng.shuffle(sites)
            for site in sites[: (a.n if kind == "py" else min(a.n, 3))]:
                if kind == "py":
                    mut = apply_py(orig, site)
                    where, old, new = site[0], site[3], site[4]
                    try:
                        compile(mut, rel, "exec")
                    except SyntaxError:
                        results.append(dict(file=rel, line=where, old=old, new=new, status="invalid")); continue
                else:
                    mut = orig[: site[0]] + site[3] + orig[site[1]:]
                    where, old, new = orig.count("\n", 0, site[0]) + 1, site[2], site[3]
                    try:
                        json.loads(mut)
                    except ValueError:
                        results.append(dict(file=rel, line=where, old=old, new=new, status="invalid")); continue
                path.write_text(mut, encoding="utf-8")
                try:
                    rc = sh(cmd, WT, a.timeout)
                finally:
                    path.write_text(orig, encoding="utf-8")
                st = "survived" if rc == 0 else ("killed(timeout)" if rc == 124 else "killed")
                results.append(dict(file=rel, line=where, old=old, new=new, status=st))
    finally:
        if not a.keep:
            subprocess.run(["git", "worktree", "remove", "--force", str(WT)], cwd=REPO)
    REPORT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    surv = [r for r in results if r["status"] == "survived"]
    print(f"\nTOTAL {len(results)}  killed {sum(r['status'].startswith('killed') for r in results)}  survived {len(surv)}  invalid {sum(r['status']=='invalid' for r in results)}")
    for r in surv:
        print(f"  survivor: {r['file']}:{r['line']} {r['old']} -> {r['new']}")
    sys.exit(1 if surv else 0)

if __name__ == "__main__":
    main()
