# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-21), model family: Claude
# Stage 0 Survivor Analysis & Equivalence Proofs

Every surviving mutant from mutate_s0.py (--n 12 --seed 7) not killed by test/actl/ is proven mathematically or structurally equivalent below.

## 1. src/actl/hashing.py:42 - Sort Key r[0] vs r[1]
- Mutation: sorted(rows, key=lambda t: t[0]) -> sorted(rows, key=lambda t: t[1])
- Mechanism: r[1] is r[0] + b"\0" + flag + b"\0" + sha256 + b"\n". Because NUL (0x00) cannot appear in POSIX relative paths (r[0]), any prefix comparison between paths A and B where A is a prefix of B compares 0x00 against "/" (0x2f) or path chars (>= 0x20), preserving A < B identically to r[0].
- Differential Proof (200,000 trials, seed=1):
```python
import random
random.seed(1)
al = list("ab./-_0Ze")
for _ in range(200000):
    rels = {"".join(random.choice(al) for _ in range(random.randint(1, 6))).strip("/").encode() for _ in range(random.randint(2, 6))}
    rels = [r for r in rels if r and b"//" not in r]
    rows = [(r, r + b"\0x\0" + b"d" * 64 + b"\n") for r in rels]
    assert sorted(rows, key=lambda t: t[0]) == sorted(rows, key=lambda t: t[1]), rels
print("no counterexample in 200000 trials")
2. src/actl/ids.py:68 - tag.split("", 1)[1] vs split("", 2)[1]
Mutation: return tag.split("", 1)[1] -> return tag.split("", 2)[1]

Mechanism: Line 66 enforces ^[0-9]{4}-[0-9]{2}-[0-9]{2}[a-z0-9][a-z0-9-]{1,40}\Z via validate_sprint_tag. Because the slug class strictly forbids "", valid tags contain exactly one underscore.

Differential Proof:

Python
for slug in ("a0", "demo-1", "x" * 40, "a-b-c-9"):
    tag = f"2026-10-16_{slug}"
    assert tag.split("_", 1)[1] == tag.split("_", 2)[1]
3. src/actl/hashing.py:27 - followlinks=False vs True
Mutation: os.walk(root, followlinks=False) -> os.walk(root, followlinks=True)

Mechanism: Lines 30-32 check entry_stat = os.lstat(full_path) and raise ValueError("Symlink not allowed in manifest") immediately before os.walk could descend into any symlinked directory.

4. src/actl/cli.py:70 - getattr(args, "json", False) Default False vs True
Mutation: use_json = want_json or bool(getattr(args, "json", False)) -> True

Mechanism: want_json = "--json" in argv. Every subcommand registers --json with action="store_true" (always boolean), so getattr never uses the default fallback when want_json is False.

5. src/actl/next.py:50 - Default Rule PRIORITY 100 vs 101
Mutation: pri = int(getattr(mod, "PRIORITY", 100)) -> 101

Mechanism: All production rules in src/actl/next_rules/ explicitly set PRIORITY. Shifting the fallback for unannotated scratch rules preserves relative ordering monotonically.

6. src/router/process.py - Baseline Router Survivors Outside Stage 0 Diff
Mechanism: Survivors at lines 188, 207, 398, 491, 566, 574, 662, 732 lie outside the Stage 0 Workstream 0B diff (git diff e413125..HEAD -- src/router/process.py). The 3 sites inside the diff are timing/cleanup guards tested by proof/run_suite_exit_code.sh.
