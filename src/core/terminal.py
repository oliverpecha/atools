import os
import sys
import re
import textwrap

USE_COLOR = os.environ.get("NO_COLOR") is None and "--no-color" not in sys.argv

class C:
    RESET   = "\033[0m"  if USE_COLOR else ""
    BOLD    = "\033[1m"  if USE_COLOR else ""
    DIM     = "\033[2m"  if USE_COLOR else ""
    ITALIC  = "\033[3m"  if USE_COLOR else ""
    RED     = "\033[31m" if USE_COLOR else ""
    GREEN   = "\033[32m" if USE_COLOR else ""
    YELLOW  = "\033[33m" if USE_COLOR else ""
    BLUE    = "\033[34m" if USE_COLOR else ""
    MAGENTA = "\033[35m" if USE_COLOR else ""
    CYAN    = "\033[36m" if USE_COLOR else ""
    GRAY    = "\033[90m" if USE_COLOR else ""

def get_wrap_width(margin: int = 4) -> int:
    cols = None
    for fd in (sys.stdout, sys.stderr, sys.stdin):
        try:
            if hasattr(fd, "fileno"):
                cols = os.get_terminal_size(fd.fileno()).columns
                if cols and cols > 20:
                    break
        except Exception:
            pass
    if not cols:
        try:
            cols = int(os.environ.get("COLUMNS", 80))
        except Exception:
            cols = 80
    return max(40, cols - margin)

def wrap_indent(text: str, prefix: str = "    │ ", first_prefix: str = None) -> str:
    if first_prefix is None:
        first_prefix = prefix
    width = get_wrap_width(margin=2)
    lines = text.splitlines()
    out = []
    for line in lines:
        if not line.strip():
            out.append(prefix.rstrip())
            continue
        wrapper = textwrap.TextWrapper(
            width=width,
            initial_indent=first_prefix if not out else prefix,
            subsequent_indent=prefix,
            break_long_words=True,
            break_on_hyphens=False
        )
        out.append(wrapper.fill(line.strip()))
    return "\n".join(out)
