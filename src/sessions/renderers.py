import re
from core.terminal import C, get_wrap_width, wrap_indent

def format_inline_md(s: str) -> str:
    code_blocks = []
    def save_code(m):
        code_blocks.append(f"{C.CYAN}{m.group(1)}{C.RESET}")
        return f"\x00CODE_{len(code_blocks)-1}\x00"

    s = re.sub(r"`([^`]+)`", save_code, s)
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: f"{C.BOLD}{m.group(1)}{C.RESET}", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", lambda m: f"{C.ITALIC}{m.group(1)}{C.RESET}", s)
    for i, repl in enumerate(code_blocks):
        s = s.replace(f"\x00CODE_{i}\x00", repl)
    return s

def render_tool(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        s_line = line.strip()
        if not s_line:
            out.append("")
            continue
        out.append(f"  {line}")
    return "\n".join(out)

def render_markdown(text: str, base_pad: str = "  ") -> str:
    lines = text.splitlines()
    out = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            out.append(f"{base_pad}    {C.GRAY}│{C.RESET} {line}")
            continue
        if line.startswith("# "):
            out.append(f"\n{base_pad}{C.BOLD}{C.MAGENTA}{line[2:].strip().upper()}{C.RESET}")
        elif line.startswith("## "):
            out.append(f"\n{base_pad}{C.BOLD}{C.BLUE}■ {line[3:].strip()}{C.RESET}")
        elif line.startswith("### "):
            out.append(f"\n{base_pad}  {C.BOLD}{C.CYAN}▸ {line[4:].strip()}{C.RESET}")
        else:
            out.append(wrap_indent(format_inline_md(line), prefix=base_pad, first_prefix=base_pad))
    return "\n".join(out)
