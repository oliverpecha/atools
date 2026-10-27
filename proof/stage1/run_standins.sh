#!/usr/bin/env bash
# Authored-by: Cursor-S1 (Grok 4.6)
# Gate-D-remediation: executable 3-stand-in vacuity harness (GD-01).
# Runs P-S1-01 and P-S1-03..P-S1-29 (27 behavioral proofs) against:
#   empty_module, always_pass_stub, always_fail_stub
# Classifies each outcome as IMPORT, SETUP, ASSERT, ENV, PASS, or OTHER.
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
  local kind="$1"
  local overlay="$2"
  rm -rf "$overlay"
  mkdir -p "$overlay"
  cp -a "${REPO_DIR}/src/actl" "${overlay}/actl"
  case "$kind" in
    empty_module)
      rm -f "${overlay}/actl/verify.py" "${overlay}/actl/session.py"
      rm -f "${overlay}/actl/cmd_verify_impl.py" "${overlay}/actl/cmd_dispatch_impl.py"
      rm -f "${overlay}/actl/cmd_wait.py" "${overlay}/actl/cmd_selftest.py"
      rm -f "${overlay}/actl/next_rules/phase3.py"
      ;;
    always_pass_stub) write_pass_stub "$overlay" ;;
    always_fail_stub) write_fail_stub "$overlay" ;;
    *) echo "unknown stand-in $kind" >&2; return 2 ;;
  esac
}

classify_log() {
  local log="$1" rc="$2"
  if grep -q 'FAIL: fixture_s1:' "$log" 2>/dev/null; then
    echo SETUP
  elif grep -q 'cannot import' "$log" 2>/dev/null || grep -q 'No module named' "$log" 2>/dev/null; then
    echo IMPORT
  elif grep -q '^FAIL:' "$log" 2>/dev/null; then
    echo ASSERT
  elif [[ "$rc" -eq 4 ]] || grep -q 'ENVFAIL:' "$log" 2>/dev/null; then
    echo ENV
  elif [[ "$rc" -eq 0 ]]; then
    echo PASS
  else
    echo OTHER
  fi
}

SUMMARY="${OUT_DIR}/summary.txt"
: > "$SUMMARY"
MATRIX="${OUT_DIR}/matrix.tsv"
printf 'standin\tproof\trc\tclass\treason\n' > "$MATRIX"

overall_fail=0
for kind in empty_module always_pass_stub always_fail_stub; do
  overlay="$(mktemp -d /tmp/actl-standin-${kind}.XXXXXX)"
  prepare_overlay "$kind" "$overlay"
  rejected=0
  total=0
  echo "=== stand-in [${kind}] ===" | tee -a "$SUMMARY"
  for proof in "${BEHAVIORAL[@]}"; do
    total=$((total + 1))
    log="${OUT_DIR}/${kind}_${proof}.log"
    export PYTHONPATH="${overlay}:${REPO_DIR}/src"
    export ACTL_REPO="$REPO_DIR"
    export PYTHONDONTWRITEBYTECODE=1
    bash "${REPO_DIR}/proof/stage1/${proof}.sh" >"$log" 2>&1
    rc=$?
    cls="$(classify_log "$log" "$rc")"
    reason="$(grep -m1 -E '^(FAIL:|OK:)' "$log" 2>/dev/null | tr '\t' ' ' | cut -c1-200 || true)"
    printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$proof" "$rc" "$cls" "$reason" >> "$MATRIX"
    if [[ "$rc" -ne 0 ]]; then
      rejected=$((rejected + 1))
    fi
    echo "  ${proof}: rc=${rc} class=${cls}" | tee -a "$SUMMARY"
  done
  echo "Stand-in [${kind}]: ${rejected}/${total} rejected (exit != 0)" | tee -a "$SUMMARY"
  if [[ "$rejected" -ne "$total" ]]; then
    overall_fail=1
  fi
  rm -rf "$overlay"
done

echo "Matrix: $MATRIX" | tee -a "$SUMMARY"
if [[ "$overall_fail" -ne 0 ]]; then
  echo "FAIL: one or more stand-ins was not fully rejected" | tee -a "$SUMMARY"
  exit 1
fi
echo "ALL 3 STAND-INS REJECTED BY 100% OF BEHAVIORAL PROOFS." | tee -a "$SUMMARY"
exit 0
