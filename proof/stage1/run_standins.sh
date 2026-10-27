#!/usr/bin/env bash
# Authored-by: Cursor-S1 (Grok 4.6)
# Gate-D-remediation: executable 3-stand-in vacuity harness (GD-01).
# Runs P-S1-01 and P-S1-03..P-S1-29 (27 behavioral proofs) against:
#   empty_module, always_pass_stub, always_fail_stub
# Classifies each outcome as IMPORT, SETUP, ASSERT, ENV, PASS, or OTHER.
# empty_module IMPORT|ASSERT is a designed rejection (module absent).
# always_pass_stub and always_fail_stub must be ASSERT-only (behavioral).
set -uo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR" || exit 4
OUT_DIR="${REPO_DIR}/proof/out/standins"
mkdir -p "$OUT_DIR"

BEHAVIORAL=(
  P-S1-01 P-S1-03 P-S1-04 P-S1-05 P-S1-06 P-S1-07 P-S1-08 P-S1-09
  P-S1-10 P-S1-11 P-S1-12 P-S1-13 P-S1-14 P-S1-15 P-S1-16 P-S1-17
  P-S1-18 P-S1-20 P-S1-21 P-S1-22 P-S1-23 P-S1-24 P-S1-25 P-S1-26
  P-S1-27 P-S1-28 P-S1-29
)

write_pass_stub() {
  # root is $overlay/src (mini-repo layout: $overlay/src/actl/...)
  local root="$1"
  cat > "${root}/actl/verify.py" <<'PY'
class StepResult:
    def __init__(self, id, cmd="", exit_code=0, output_sha256=None, output_tail="", duration_ms=0, failing_line=None):
        self.id = id
        self.cmd = cmd
        self.exit_code = exit_code
        self.output_sha256 = output_sha256 or ("0" * 64)
        self.output_tail = output_tail
        self.duration_ms = duration_ms
        self.failing_line = failing_line
    def to_verification_step(self):
        return {"id": self.id, "cmd": self.cmd, "exit_code": self.exit_code, "output_sha256": self.output_sha256}

def sanitize_failing_line(text):
    return (text or "")[:300]

def _steps():
    return [StepResult(x) for x in ("G1", "G2", "G3", "G4", "G5", "G6")]

def check_guards(*a, **k):
    return _steps()

def run_selftests():
    return [StepResult(f"selftest:G{i}") for i in range(1, 7)]

def run_o1(*a, **k):
    return [StepResult(i) for i in ("O1:01_public.sh", "O1:02_no_email.sh", "O1:03_private_404.sh", "O1:probe.sh")]

def run_o2(*a, **k):
    return [StepResult("O2", cmd="python3 -m pytest test -q -rf --junitxml=<tmp_xml>")]

def verify_impl(*a, **k):
    steps = [s.to_verification_step() for s in _steps()]
    return {
        "kind": "verification", "seq": 7, "parent": "closure-006.json",
        "id": "verification-007", "stage": "offline", "oracle": "oracle-003",
        "contract": "contract-005", "head": "0" * 40, "exit_code": 0,
        "steps": steps, "failing_step": None, "failing_line": None,
        "tripwires": [], "halt": None, "session": None,
    }
PY
  cat > "${root}/actl/session.py" <<'PY'
def start_session(*a, **k):
    return 0
def wait_session(*a, **k):
    return {"name": a[0] if a else "", "exit_code": 0, "hard_cap": False, "lost": False, "log_sha256": "0" * 64}
def archive_session_log(*a, **k):
    return "0" * 64
def scan_tripwires(*a, **k):
    return []
def compute_wait_timeout(*a, **k):
    return 2733
PY
  mkdir -p "${root}/actl/next_rules"
  echo "PRIORITY = 30" > "${root}/actl/next_rules/phase3.py"
  echo "def evaluate(*a, **k):" >> "${root}/actl/next_rules/phase3.py"
  echo "    return {\"action\": \"done\", \"command\": \"\", \"reason\": \"stub\"}" >> "${root}/actl/next_rules/phase3.py"
  for m in cmd_verify_impl cmd_dispatch_impl cmd_wait cmd_selftest; do
    echo "def register(sp):" > "${root}/actl/${m}.py"
    echo "    return None" >> "${root}/actl/${m}.py"
  done
}

write_fail_stub() {
  local root="$1"
  cat > "${root}/actl/verify.py" <<'PY'
class StepResult:
    def __init__(self, id, cmd="", exit_code=1, output_sha256=None, output_tail="FAIL", duration_ms=0, failing_line="FAIL"):
        self.id = id
        self.cmd = cmd
        self.exit_code = exit_code
        self.output_sha256 = output_sha256 or ("f" * 64)
        self.output_tail = output_tail
        self.duration_ms = duration_ms
        self.failing_line = failing_line
    def to_verification_step(self):
        return {"id": self.id, "cmd": self.cmd, "exit_code": self.exit_code, "output_sha256": self.output_sha256}

def sanitize_failing_line(text):
    return "FAIL"

def check_guards(*a, **k):
    return [StepResult(x) for x in ("G1", "G2", "G3", "G4", "G5", "G6")]

def run_selftests():
    return [StepResult(f"selftest:G{i}", exit_code=3) for i in range(1, 7)]

def run_o1(*a, **k):
    return [StepResult("O1:01_public.sh")]

def run_o2(*a, **k):
    return [StepResult("O2")]

def verify_impl(*a, **k):
    return {
        "kind": "verification", "seq": 7, "parent": None, "id": "verification-007",
        "stage": "offline", "oracle": "oracle-003", "contract": "contract-005",
        "head": "0" * 40, "exit_code": 1, "steps": [], "failing_step": "G3",
        "failing_line": "FAIL", "tripwires": [], "halt": None, "session": None,
    }
PY
  cat > "${root}/actl/session.py" <<'PY'
def start_session(*a, **k):
    raise ValueError("always_fail_stub")
def wait_session(*a, **k):
    return {"name": "", "exit_code": None, "hard_cap": False, "lost": True, "log_sha256": None}
def archive_session_log(*a, **k):
    return None
def scan_tripwires(*a, **k):
    return [{"source": "log", "line_no": 1, "pattern": "records/", "excerpt": "records/"}]
def compute_wait_timeout(*a, **k):
    return 0
PY
  mkdir -p "${root}/actl/next_rules"
  echo "PRIORITY = 30" > "${root}/actl/next_rules/phase3.py"
  echo "def evaluate(*a, **k):" >> "${root}/actl/next_rules/phase3.py"
  echo "    return {\"action\": \"dispatch\", \"command\": \"actl dispatch-impl --sprint x\", \"reason\": \"stub\"}" >> "${root}/actl/next_rules/phase3.py"
  for m in cmd_verify_impl cmd_dispatch_impl cmd_wait cmd_selftest; do
    echo "def register(sp):" > "${root}/actl/${m}.py"
    echo "    return None" >> "${root}/actl/${m}.py"
  done
}

prepare_overlay() {
  # Mini-repo: $overlay/{src/actl,schemas,fixtures}; stubs written under src/actl.
  local kind="$1"
  local overlay="$2"
  local src="${overlay}/src"
  rm -rf "$overlay"
  mkdir -p "$src"
  cp -a "${REPO_DIR}/src/actl" "${src}/actl"
  case "$kind" in
    empty_module)
      rm -f "${src}/actl/verify.py" "${src}/actl/session.py"
      rm -f "${src}/actl/cmd_verify_impl.py" "${src}/actl/cmd_dispatch_impl.py"
      rm -f "${src}/actl/cmd_wait.py" "${src}/actl/cmd_selftest.py"
      rm -f "${src}/actl/next_rules/phase3.py"
      ;;
    always_pass_stub) write_pass_stub "$src" ;;
    always_fail_stub) write_fail_stub "$src" ;;
    *) echo "unknown stand-in $kind" >&2; return 2 ;;
  esac
}

classify_log() {
  # Fail-closed order (NEW-01 + R7): rc==0 PASS; rc==4 ENV;
  # SETUP (fixture_s1 / sandbox setup failed / FAIL: fixture);
  # IMPORT (cannot import / No module named);
  # ASSERT only on explicit FAIL: S1-R / FAIL: S1A- markers that are not SETUP;
  # unrecognized FAIL: -> OTHER.
  local log="$1" rc="$2"
  local fail_line
  if [[ "$rc" -eq 0 ]]; then
    echo PASS
    return
  fi
  if [[ "$rc" -eq 4 ]] || grep -q 'ENVFAIL:' "$log" 2>/dev/null; then
    echo ENV
    return
  fi
  fail_line="$(grep -m1 -E '^FAIL:' "$log" 2>/dev/null || true)"
  if [[ -z "$fail_line" ]]; then
    echo OTHER
    return
  fi
  if [[ "$fail_line" == *"fixture_s1"* ]] \
    || [[ "$fail_line" == *"sandbox setup failed"* ]] \
    || [[ "$fail_line" == FAIL:\ fixture* ]] \
    || grep -q 'FAIL: fixture_s1:' "$log" 2>/dev/null; then
    echo SETUP
    return
  fi
  if [[ "$fail_line" == *"cannot import"* ]] || [[ "$fail_line" == *"No module named"* ]]; then
    echo IMPORT
    return
  fi
  if [[ "$fail_line" == FAIL:\ S1-R* ]] || [[ "$fail_line" == FAIL:\ S1A-* ]]; then
    echo ASSERT
    return
  fi
  echo OTHER
}

# --selftest: GPT counterexample must classify as SETUP, not ASSERT.
if [[ "${1:-}" == "--selftest" ]]; then
  _st_log="$(mktemp)"
  printf '%s\n' 'FAIL: S1-R15.3: sandbox setup failed' >"$_st_log"
  _st_cls="$(classify_log "$_st_log" 1)"
  rm -f "$_st_log"
  if [[ "$_st_cls" != "SETUP" ]]; then
    echo "FAIL: --selftest expected SETUP for 'FAIL: S1-R15.3: sandbox setup failed', got ${_st_cls}"
    exit 1
  fi
  echo "OK: run_standins --selftest classify_log SETUP"
  exit 0
fi

SUMMARY="${OUT_DIR}/summary.txt"
: > "$SUMMARY"
MATRIX="${OUT_DIR}/matrix.tsv"
printf 'standin\tproof\trc\tclass\treason\n' > "$MATRIX"

# Expected behavioral class per stand-in (not merely rc != 0).
# empty_module -> IMPORT or ASSERT (not PASS); always_*_stub -> ASSERT
# (0 IMPORT). Do not compare class to the literal string IMPORT_OR_ASSERT.
print_matrix_class_counts() {
  local standin="$1"
  local c_IMPORT=0 c_SETUP=0 c_ASSERT=0 c_ENV=0 c_PASS=0 c_OTHER=0
  local cls
  while IFS=$'\t' read -r _s _p _rc cls _rest; do
    case "$cls" in
      IMPORT) c_IMPORT=$((c_IMPORT + 1)) ;;
      SETUP)  c_SETUP=$((c_SETUP + 1)) ;;
      ASSERT) c_ASSERT=$((c_ASSERT + 1)) ;;
      ENV)    c_ENV=$((c_ENV + 1)) ;;
      PASS)   c_PASS=$((c_PASS + 1)) ;;
      class)  continue ;;
      *)      c_OTHER=$((c_OTHER + 1)) ;;
    esac
  done < <(awk -F'\t' -v s="$standin" 'NR==1 || $1==s {print}' "$MATRIX")
  echo "matrix.tsv [${standin}] class counts: IMPORT=${c_IMPORT} SETUP=${c_SETUP} ASSERT=${c_ASSERT} ENV=${c_ENV} PASS=${c_PASS} OTHER=${c_OTHER}"
}

overall_fail=0
for kind in empty_module always_pass_stub always_fail_stub; do
  # Mini-repo overlay: $overlay/src/actl + schemas/fixtures symlinks so
  # schemas.REPO_ROOT (parents[2] of src/actl/*.py) resolves to $overlay.
  overlay="$(mktemp -d /tmp/actl-standin-${kind}.XXXXXX)"
  prepare_overlay "$kind" "$overlay"
  ln -sfn "${REPO_DIR}/schemas" "${overlay}/schemas"
  ln -sfn "${REPO_DIR}/fixtures" "${overlay}/fixtures"
  if [[ -d "${REPO_DIR}/config" ]]; then
    ln -sfn "${REPO_DIR}/config" "${overlay}/config"
  fi
  c_IMPORT=0; c_SETUP=0; c_ASSERT=0; c_ENV=0; c_PASS=0; c_OTHER=0
  total=0
  matched=0
  if [[ "$kind" == "empty_module" ]]; then
    expect_desc="IMPORT|ASSERT (not PASS)"
  else
    expect_desc="ASSERT (0 IMPORT, 0 OTHER, 0 PASS)"
  fi
  echo "=== stand-in [${kind}] (expect class=${expect_desc}) ===" | tee -a "$SUMMARY"
  for proof in "${BEHAVIORAL[@]}"; do
    total=$((total + 1))
    log="${OUT_DIR}/${kind}_${proof}.log"
    # Overlay first so stub verify/session/phase3 win; REPO src supplies router/core/sessions.
    export ACTL_STANDIN_OVERLAY=1
    export PYTHONPATH="${overlay}/src:${REPO_DIR}/src"
    export ACTL_REPO="$REPO_DIR"
    export PYTHONDONTWRITEBYTECODE=1
    bash "${REPO_DIR}/proof/stage1/${proof}.sh" >"$log" 2>&1
    rc=$?
    cls="$(classify_log "$log" "$rc")"
    reason="$(grep -m1 -E '^(FAIL:|OK:)' "$log" 2>/dev/null | tr '\t' ' ' | cut -c1-200 || true)"
    printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$proof" "$rc" "$cls" "$reason" >> "$MATRIX"
    case "$cls" in
      IMPORT) c_IMPORT=$((c_IMPORT + 1)) ;;
      SETUP)  c_SETUP=$((c_SETUP + 1)) ;;
      ASSERT) c_ASSERT=$((c_ASSERT + 1)) ;;
      ENV)    c_ENV=$((c_ENV + 1)) ;;
      PASS)   c_PASS=$((c_PASS + 1)) ;;
      *)      c_OTHER=$((c_OTHER + 1)) ;;
    esac
    # empty_module: IMPORT or ASSERT (never PASS). stubs: ASSERT only.
    if [[ "$kind" == "empty_module" ]]; then
      if [[ "$cls" == "IMPORT" || "$cls" == "ASSERT" ]]; then
        matched=$((matched + 1))
      fi
    elif [[ "$cls" == "ASSERT" ]]; then
      matched=$((matched + 1))
    fi
    echo "  ${proof}: rc=${rc} class=${cls}" | tee -a "$SUMMARY"
  done
  echo "Stand-in [${kind}] class counts: IMPORT=${c_IMPORT} SETUP=${c_SETUP} ASSERT=${c_ASSERT} ENV=${c_ENV} PASS=${c_PASS} OTHER=${c_OTHER} (total=${total})" | tee -a "$SUMMARY"
  echo "Stand-in [${kind}]: ${matched}/${total} matched expected class (${expect_desc})" | tee -a "$SUMMARY"
  kind_fail=0
  if [[ "$kind" == "empty_module" ]]; then
    # empty_module may be IMPORT or ASSERT (CLI-without-import) but never PASS.
    if [[ "$c_PASS" -ne 0 ]] || [[ $((c_IMPORT + c_ASSERT)) -ne "$total" ]]; then
      echo "FAIL: empty_module expected IMPORT|ASSERT only (0 PASS); got IMPORT=${c_IMPORT} ASSERT=${c_ASSERT} PASS=${c_PASS} SETUP=${c_SETUP} ENV=${c_ENV} OTHER=${c_OTHER}" | tee -a "$SUMMARY"
      kind_fail=1
      overall_fail=1
    fi
  else
    # Stubs must be ASSERT for all 27; 0 IMPORT, 0 OTHER, 0 PASS.
    if [[ "$c_ASSERT" -ne "$total" ]] || [[ "$c_IMPORT" -ne 0 ]] || [[ "$c_OTHER" -ne 0 ]] || [[ "$c_PASS" -ne 0 ]]; then
      echo "FAIL: ${kind} expected ${total} ASSERT and 0 IMPORT/OTHER/PASS; got ASSERT=${c_ASSERT} IMPORT=${c_IMPORT} OTHER=${c_OTHER} PASS=${c_PASS}" | tee -a "$SUMMARY"
      kind_fail=1
      overall_fail=1
    fi
  fi
  if [[ "$kind_fail" -ne 0 ]]; then
    print_matrix_class_counts "$kind" | tee -a "$SUMMARY"
    # Surface OTHER proof ids for stub thickening / FAIL: S1-R... fixes.
    if [[ "$c_OTHER" -ne 0 ]]; then
      awk -F'\t' -v s="$kind" '$1==s && $4=="OTHER" {print "OTHER proof: "$2" rc="$3" reason="$5}' "$MATRIX" | tee -a "$SUMMARY"
    fi
  fi
  rm -rf "$overlay"
done

echo "Matrix: $MATRIX" | tee -a "$SUMMARY"
if [[ "$overall_fail" -ne 0 ]]; then
  echo "Per-stand-in class counts from matrix.tsv:" | tee -a "$SUMMARY"
  for kind in empty_module always_pass_stub always_fail_stub; do
    print_matrix_class_counts "$kind" | tee -a "$SUMMARY"
  done
  echo "FAIL: stand-in class isolation did not match expected ASSERT/IMPORT matrix" | tee -a "$SUMMARY"
  exit 1
fi
echo "ALL 3 STAND-INS MATCHED EXPECTED BEHAVIORAL CLASSES." | tee -a "$SUMMARY"
exit 0
