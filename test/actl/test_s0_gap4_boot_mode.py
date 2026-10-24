# Authored-by: Gemini 2.5 Pro (Google), Owner-attested
import os, stat
from pathlib import Path
from helpers import need

def test_boot_trampoline_mode_is_0755(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(tmp_path / "sess"))
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(tmp_path / "logs"))
    proc = need("router.process")
    boot = proc.create_runner_script(
        session_name="bootmode", engine_script="/bin/true", dispatch_args=["auto"],
        watchdog_timeout="off", kill_grace="3s", tier="cheap", model="auto",
        engine="cursor", log_file=tmp_path / "logs" / "bootmode.log")
    assert stat.S_IMODE(os.lstat(boot).st_mode) == 0o755
