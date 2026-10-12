import sys
import os
import re
import json
import datetime
from pathlib import Path

from core.terminal import C, get_wrap_width, wrap_indent
from sessions.storage import get_unique_session_files, resolve_session_path, delete_sessions
from sessions.reader import (
    get_session_meta,
    enrich_meta_from_transcript,
    format_pretty_utc,
    format_table_utc,
    parse_embedded_timestamp,
    clean_text,
)
from sessions.renderers import format_inline_md, render_markdown

CONTEXT_PLATEAU_PEAK = 86000
CONTEXT_PLATEAU_FLOOR = 62000
COMPACTION_START_TURN = 32
ESTIMATED_TOOL_RETURN_TOKENS = 3200
ESTIMATED_REASONING_PER_TURN = 580

def is_harness_prompt(txt: str) -> bool:
    t = txt.strip().lower()
    return any(sig in t for sig in [
        "briefly inform the user about the task result",
        "task complete. please summarize",
        "perform any follow-up actions (if needed)",
        "the background task has finished",
    ])

def format_tool(name: str, args) -> str:
    if isinstance(args, dict):
        if name == "Shell" or "command" in args:
            cmd = args.get("command", "")
            lines = cmd.splitlines() if cmd else []
            first = lines[0] if lines else ""
            extra = f" {C.GRAY}(+{len(lines)-1} lines){C.RESET}" if len(lines) > 1 else ""
            desc = args.get("description", "")
            desc_tag = f" {C.GRAY}[{desc}]{C.RESET}" if desc else ""
            header = f"{C.YELLOW}${C.RESET}{desc_tag} {C.BOLD}{first}{C.RESET}{extra}"
            if len(lines) > 1:
                preview = "\n".join(f"    {C.GRAY}│{C.RESET} {l}" for l in lines[1:])
                return f"{header}\n{preview}"
            return header

        if name == "Read" or ("path" in args and name not in ("Write", "StrReplace")):
            path = args.get("path", "")
            lines_spec = ""
            if "start_line" in args or "end_line" in args:
                s = args.get("start_line", 1)
                e = args.get("end_line", "")
                lines_spec = f" {C.GRAY}lines {s}-{e}{C.RESET}" if e else f" {C.GRAY}line {s}+{C.RESET}"
            return f"{C.CYAN}📖 Read{C.RESET} {path}{lines_spec}"

        if name == "Write":
            path = args.get("path", "")
            content = args.get("contents", args.get("content", ""))
            lines = content.splitlines() if isinstance(content, str) else []
            count_str = f" {C.GREEN}+{len(lines)}{C.RESET}" if lines else ""
            return f"{C.BLUE}📝 Edited{C.RESET} {path}{count_str}"

        if name == "StrReplace":
            path = args.get("path", "")
            old_str = str(args.get("old_string", args.get("old_str", "")))
            new_str = str(args.get("new_string", args.get("new_str", "")))
            old_lines = old_str.splitlines()
            new_lines = new_str.splitlines()
            diff_badge = f" {C.GREEN}+{len(new_lines)}{C.RESET} {C.RED}-{len(old_lines)}{C.RESET}"
            return f"{C.BLUE}📝 Edited{C.RESET} {path}{diff_badge}"

        if name == "Glob":
            return f"{C.MAGENTA}📁 Globbed{C.RESET} \"{args.get('glob_pattern', args.get('pattern', ''))}\""

        if name == "Grep":
            return f"{C.MAGENTA}🔍 Grepped{C.RESET} \"{args.get('pattern', '')}\""

        items = [f"{k}={repr(v)[:30]}" for k, v in args.items() if k not in ("contents", "new_string", "old_string", "content")]
        return f"{C.CYAN}⚙️ {name}{C.RESET}: {', '.join(items)}"
    return f"{C.CYAN}⚙️ {name}{C.RESET}: {str(args)[:70]}"

def show_session(target_uuid: str, summary_only: bool = False) -> None:
    fpath, full_id = resolve_session_path(target_uuid)
    if not fpath:
        print(f"Error: Session '{target_uuid}' not found.")
        sys.exit(1)

    meta = get_session_meta(full_id)
    meta = enrich_meta_from_transcript(meta, fpath)

    is_frontier = any(x in meta["model"].lower() for x in ("sonnet", "opus", "gpt-4", "o1", "o3"))
    in_rate = 3.00 if is_frontier else 0.75
    cache_rate = 0.30 if is_frontier else 0.075
    out_rate = 15.00 if is_frontier else 3.50

    current_context = 4200
    prev_context = 0
    cum_cached = 0
    cum_fresh = 0
    cum_out = 0
    user_turns = 0
    agent_turns = 0
    tool_calls = 0
    dialogue_chars = 0
    dialogue = []

    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue

            role = entry.get("role", "").lower()
            msg = entry.get("message", entry.get("content", {}))

            if role in ("user", "human"):
                user_turns += 1
                txt = clean_text(msg)
                dialogue_chars += len(txt)
                u_toks = max(1, int(len(txt) / 3.7))
                current_context = min(CONTEXT_PLATEAU_PEAK, current_context + u_toks)
                dialogue.append(["USER", txt])

            elif role in ("assistant", "agent"):
                agent_turns += 1
                raw_txt = str(msg)
                dialogue_chars += len(raw_txt)
                out_toks = max(10, int(len(raw_txt) / 3.7)) + ESTIMATED_REASONING_PER_TURN
                cum_out += out_toks

                active_ceiling = (
                    CONTEXT_PLATEAU_PEAK
                    if agent_turns <= COMPACTION_START_TURN
                    else max(CONTEXT_PLATEAU_FLOOR, CONTEXT_PLATEAU_PEAK - int((agent_turns - COMPACTION_START_TURN) * 550))
                )

                cached = min(prev_context, active_ceiling)
                fresh = max(0, min(current_context, active_ceiling) - cached)
                cum_cached += cached
                cum_fresh += fresh

                current_context = min(active_ceiling, current_context + out_toks)
                prev_context = current_context

                blocks = msg.get("content", msg) if isinstance(msg, dict) else msg
                if isinstance(blocks, str):
                    blocks = [{"type": "text", "text": blocks}]
                elif not isinstance(blocks, list):
                    blocks = [blocks]

                for b in blocks:
                    if isinstance(b, dict):
                        if b.get("type") == "text" and b.get("text", "").strip():
                            raw_t = b.get("text", "").strip()
                            is_thought = raw_t.startswith("**") and "\n" in raw_t and not raw_t.startswith("###")
                            dialogue.append(["THOUGHT" if is_thought else "AGENT", raw_t])
                        elif b.get("type") in ("tool_use", "tool_call") or "name" in b:
                            tool_calls += 1
                            t_name = b.get("name", "Tool")
                            t_in = b.get("input", b.get("arguments", {}))
                            dialogue.append(["TOOL", format_tool(t_name, t_in)])
                            current_context = min(active_ceiling, current_context + ESTIMATED_TOOL_RETURN_TOKENS)

            elif "tool" in role:
                tool_calls += 1

    total_in = cum_cached + cum_fresh
    total_tokens = total_in + cum_out
    cost_cached = (cum_cached / 1e6) * cache_rate
    cost_fresh = (cum_fresh / 1e6) * in_rate
    cost_out = (cum_out / 1e6) * out_rate
    realized_cost = cost_cached + cost_fresh + cost_out
    uncached_cost = (total_in / 1e6) * in_rate + (cum_out / 1e6) * out_rate
    cache_pct = (cum_cached / total_in * 100) if total_in else 0
    blended = (realized_cost / (total_tokens / 1e6)) if total_tokens else 0
    plan_pct = (realized_cost / 20.0) * 100

    print("\n" + C.BOLD + "═" * 80 + C.RESET)
    print(f"  {C.BOLD}SESSION AUDIT:{C.RESET} {C.CYAN}{full_id}{C.RESET}")
    print(C.BOLD + "═" * 80 + C.RESET)
    print(f"  {C.BOLD}Metadata{C.RESET}")
    print(f"    Session Title:     {meta['title']}")
    print(f"    Dispatched Model:  {C.CYAN}{meta['model']}{C.RESET}")
    print(f"    Start Time (UTC):  {meta['created_utc']}")
    print(f"    End Time (UTC):    {meta['updated_utc']}")
    print(f"    Active Wall-Clock: {C.YELLOW}{meta['duration']}{C.RESET}")
    print(f"    Workspace Root:    {meta['cwd']}")
    print("  " + C.GRAY + "─" * 76 + C.RESET)
    print(f"  {C.BOLD}Heuristic Wire Reconstruction{C.RESET} {C.GRAY}(Tool-Payload & Reasoning Simulation){C.RESET}")
    print(f"    Cumulative Prompt Context:   ~{total_in:,} tokens")
    print(f"      Cache Read (Repeated):     ~{cum_cached:,} tokens ({cache_pct:.1f}%)")
    print(f"      Fresh Input (Payloads):    ~{cum_fresh:,} tokens ({100-cache_pct:.1f}%)")
    print(f"    Cumulative Output Tokens:    ~{cum_out:,} tokens")
    print(f"    Total Wire Token Volume:     ~{total_tokens:,} tokens")
    print("  " + C.GRAY + "─" * 76 + C.RESET)
    print(f"  {C.BOLD}Estimated Realized Billing{C.RESET} {C.GRAY}({meta['model']}){C.RESET}")
    print(f"    Realized Cost:               {C.GREEN}~${realized_cost:.2f}{C.RESET} {C.GRAY}(~{plan_pct:.1f}% of $20/mo plan){C.RESET}")
    print(f"    Uncached Benchmark:          ~${uncached_cost:.2f} {C.GRAY}(absorbed {100-(realized_cost/uncached_cost*100 if uncached_cost else 0):.1f}% via caching){C.RESET}")
    print(f"    Effective Blended Rate:      ~${blended:.3f} / 1M tokens")
    print("  " + C.GRAY + "─" * 76 + C.RESET)
    print(f"  {C.BOLD}Operational Telemetry{C.RESET}")
    print(f"    Turn Accounting:             {user_turns} user turns | {agent_turns} agent turns | {tool_calls} tool calls")
    print(f"    Logged Transcript Text:      ~{int(dialogue_chars / 3.7):,} dialogue tokens ({len(dialogue)} entries)")
    print(C.BOLD + "═" * 80 + C.RESET + "\n")

    if summary_only:
        return

    for item in dialogue:
        role, text = item[0], item[1]
        if role == "USER":
            if is_harness_prompt(text):
                print(f"\n{C.MAGENTA}{C.BOLD}⚡ HARNESS CALLBACK:{C.RESET}")
                print(wrap_indent(text, prefix=f"  {C.GRAY}│{C.RESET} ") + "\n")
            else:
                print(f"\n{C.CYAN}{C.BOLD}👤 USER:{C.RESET}")
                print(wrap_indent(text, prefix="  ") + "\n")
        elif role == "THOUGHT":
            lines = text.splitlines()
            title = lines[0].replace("**", "").strip() if lines else ""
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            print(f"\n  {C.GRAY}💭 {C.BOLD}{title}{C.RESET}")
            if body:
                print(wrap_indent(format_inline_md(body), prefix=f"    {C.GRAY}│{C.RESET} "))
        elif role == "AGENT":
            print(f"\n{C.GREEN}{C.BOLD}🤖 AGENT:{C.RESET}")
            print(render_markdown(text, base_pad="  ") + "\n")
        elif role == "TOOL":
            print(f"  {text}")

    print("\n" + "─" * 80)
    print(f"✨ {C.BOLD}Session {full_id[:8]}{C.RESET} · {C.CYAN}{meta['model']}{C.RESET} · {user_turns} user | {agent_turns} agent | {tool_calls} tools · {C.GREEN}~${realized_cost:.2f}{C.RESET}")
    print("─" * 80 + "\n")

def list_sessions() -> None:
    files = get_unique_session_files()
    if not files:
        print("No Cursor Agent sessions found.")
        return
    print("\n" + "=" * 116)
    print(f" {'#':<4} {'SESSION ID':<10} {'DATE / TIME (UTC)':<24} {'MODEL DISPATCHED':<22} {'DURATION':<10} {'QUERY / INTENT'}")
    print("=" * 116)
    for idx, p in enumerate(files, 1):
        uid = Path(p).parent.name[:8]
        meta = get_session_meta(uid)
        meta = enrich_meta_from_transcript(meta, p)
        dt_str = format_table_utc(meta["created_ms"]) if meta["created_ms"] else "N/A"
        query = "N/A"
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("role") in ("user", "human"):
                        cleaned = clean_text(entry.get("message", entry.get("content", {})))
                        if cleaned:
                            query = (cleaned[:38] + "..") if len(cleaned) > 38 else cleaned
                            break
        except Exception:
            pass
        print(f" {idx:<4} [{uid}]   {dt_str:<24} {meta['model']:<22} {meta['duration']:<10} {query}")
    print("=" * 116)
    print("💡 Run 'asessions <uuid>' to view full execution transcript.")
    print("💡 Run 'asessions <uuid> --summary' for metadata and token economics.")
    print("💡 Run 'asessions rm <uuid...>' to delete test sessions.\n")

def get_all_history_records():
    files = get_unique_session_files()
    records = []
    for idx, p in enumerate(files, 1):
        uid = Path(p).parent.name[:8]
        full_id = Path(p).parent.name
        meta = get_session_meta(uid)
        meta = enrich_meta_from_transcript(meta, p)
        dt_str = format_table_utc(meta["created_ms"]) if meta.get("created_ms") else "N/A"
        date_short = dt_str[:12].strip() if dt_str != "N/A" else "N/A"
        query = "N/A"
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("role") in ("user", "human"):
                        cleaned = clean_text(entry.get("message", entry.get("content", {})))
                        if cleaned:
                            query = cleaned.replace("\n", " ").strip()
                            break
        except Exception:
            pass
        records.append({
            "idx": idx,
            "uuid": uid,
            "full_id": full_id,
            "date": date_short,
            "model": meta.get("model", "-")[:16],
            "duration": meta.get("duration", "-"),
            "query": query,
        })
    return records


def get_recent_history(limit: int = 5):
    return get_all_history_records()[:limit]


def interactive_explorer() -> int:
    import contextlib
    import io
    import termios
    import tty
    import time
    import shutil
    try:
        from router.process import get_running_sessions, kill_session, stream_session
    except ImportError:
        get_running_sessions = lambda: []
        kill_session = lambda s: 0
        stream_session = lambda s: 0

    fd = sys.stdin.fileno()
    view_mode = "main"
    selected_idx = 0
    scroll_offset = 0
    prev_lines = 0

    def read_key() -> str:
        old_attr = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                return ch + seq
            return ch
        except KeyboardInterrupt:
            return "\x03"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)

    def confirm_delete_prompt(session_id: str, query: str = "") -> bool:
        q_disp = f' (\"{query[:28]}...\")' if query else ""
        sys.stdout.write(f"\r\033[2K\033[1;33m⚠️  Are you sure you want to delete session '{session_id[:8]}'{q_disp}? [y/N]: \033[0m")
        sys.stdout.flush()
        old_attr = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ch = sys.stdin.read(1)
            confirmed = ch in ("y", "Y")
            if confirmed:
                sys.stdout.write(f"\r\033[2K\033[1;32m✅ Session '{session_id[:8]}' deleted.\033[0m")
                sys.stdout.flush()
                time.sleep(0.3)
            else:
                sys.stdout.write(f"\r\033[2K\033[1;30mDeletion canceled.\033[0m")
                sys.stdout.flush()
                time.sleep(0.2)
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            return confirmed
        except Exception:
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)

    def wait_for_return(prompt_msg: str = "") -> str:
        sys.stdout.write(f"\n{C.GRAY}{'─' * 80}{C.RESET}\n")
        msg = prompt_msg or f"{C.BOLD}[Enter/Space]{C.RESET} Return to explorer   {C.BOLD}[d]{C.RESET} Delete   {C.BOLD}[q/Ctrl+C]{C.RESET} Exit"
        sys.stdout.write(f" {msg}: ")
        sys.stdout.flush()
        old_attr = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n", " "):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "return"
                elif ch in ("q", "Q", "\x03", "\x04"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "quit"
                elif ch in ("d", "D"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "delete"
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "quit"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)

    try:
        while True:
            _, term_rows = shutil.get_terminal_size((80, 24))
            term_rows = max(14, term_rows)

            buf = []
            items = []

            if view_mode == "main":
                active = get_running_sessions()
                recent = get_recent_history(limit=5)

                for a in active:
                    items.append({"type": "active", "id": a["session"], "data": a})
                for r in recent:
                    items.append({"type": "history", "id": r["uuid"], "data": r})
                items.append({"type": "switch_full", "id": "full", "label": "[h] View all past sessions (full table)"})
                items.append({"type": "quit", "id": "quit", "label": "[q] Quit to shell"})

                if selected_idx >= len(items):
                    selected_idx = max(0, len(items) - 1)

                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")
                buf.append(f" {C.BOLD}⚡ AROUTER & ASESSIONS WORKSPACE EXPLORER{C.RESET}")
                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")

                buf.append(f" {C.BOLD}[● ACTIVE SESSIONS]{C.RESET}")
                if not active:
                    buf.append(f"   {C.GRAY}(No active background sessions running){C.RESET}")
                else:
                    for idx, a in enumerate(active):
                        is_sel = (idx == selected_idx)
                        prefix = f" {C.CYAN}❯{C.RESET} " if is_sel else "   "
                        color = C.GREEN if is_sel else C.RESET
                        name_tag = f"[{a['session'][:22]}]"
                        tier_str = a.get("tier", "-")[:13]
                        elapsed_str = a.get("elapsed", "-")[:7]
                        p_text = a.get("prompt", "")
                        p_disp = (p_text[:38] + "..") if len(p_text) > 38 else (p_text if p_text else "(running)")
                        line = (
                            f"{prefix}🟢 {color}{name_tag:<24}{C.RESET}  "
                            f"{C.YELLOW}{tier_str:<14}{C.RESET}  "
                            f"{elapsed_str:<8}  "
                            f'\"{p_disp}\"'
                        )
                        buf.append(line)

                buf.append("")
                buf.append(f" {C.BOLD}[○ RECENT HISTORY (Last 5)]{C.RESET}")
                if not recent:
                    buf.append(f"   {C.GRAY}(No recent session history){C.RESET}")
                else:
                    for idx, r in enumerate(recent):
                        item_idx = len(active) + idx
                        is_sel = (item_idx == selected_idx)
                        prefix = f" {C.CYAN}❯{C.RESET} " if is_sel else "   "
                        color = C.BOLD if is_sel else C.RESET
                        uid_tag = f"[{r['uuid'][:8]}]"
                        date_str = r['date'][:11]
                        model_str = r.get("model", "-")[:13]
                        dur_str = r.get("duration", "-")[:7]
                        q_text = r.get("query", "")
                        q_disp = (q_text[:38] + "..") if len(q_text) > 38 else q_text
                        line = (
                            f"{prefix}⚪ {color}{uid_tag:<11}{C.RESET}{C.GRAY}{date_str:<13}{C.RESET}  "
                            f"{C.CYAN}{model_str:<14}{C.RESET}  "
                            f"{dur_str:<8}  "
                            f'\"{q_disp}\"'
                        )
                        buf.append(line)

                buf.append("")
                buf.append(f" {C.BOLD}[OPTIONS & BUTTONS]{C.RESET}")
                btn_start = len(active) + len(recent)
                for idx in range(btn_start, len(items)):
                    is_sel = (idx == selected_idx)
                    prefix = f" {C.CYAN}❯{C.RESET} " if is_sel else "   "
                    color = C.CYAN if is_sel else C.RESET
                    buf.append(f"{prefix}{color}{items[idx]['label']}{C.RESET}")

                buf.append(f"{C.GRAY}{'─' * 92}{C.RESET}")
                buf.append(f" {C.BOLD}Keys:{C.RESET} [↑/↓] Navigate  |  [Enter] Open  |  [d] Delete  |  [k] Kill active  |  [q] Quit")
                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")

            else:  # view_mode == "full"
                all_records = get_all_history_records()
                for r in all_records:
                    items.append({"type": "full_history", "id": r["uuid"], "data": r})
                items.append({"type": "switch_main", "id": "main", "label": "[b] Back to main explorer"})
                items.append({"type": "quit", "id": "quit", "label": "[q] Quit to shell"})

                if selected_idx >= len(items):
                    selected_idx = max(0, len(items) - 1)

                max_visible = max(6, min(14, term_rows - 8))
                rec_count = len(all_records)

                if selected_idx < rec_count:
                    if selected_idx < scroll_offset:
                        scroll_offset = selected_idx
                    elif selected_idx >= scroll_offset + max_visible:
                        scroll_offset = selected_idx - max_visible + 1
                else:
                    scroll_offset = max(0, rec_count - max_visible)

                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")
                buf.append(f" {C.BOLD}⚡ AROUTER & ASESSIONS — ALL PAST SESSIONS ({rec_count} total){C.RESET}")
                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")

                if not all_records:
                    buf.append(f"   {C.GRAY}(No historical sessions found){C.RESET}")
                else:
                    visible_slice = all_records[scroll_offset : scroll_offset + max_visible]
                    for idx_rel, r in enumerate(visible_slice):
                        real_idx = scroll_offset + idx_rel
                        is_sel = (real_idx == selected_idx)
                        prefix = f" {C.CYAN}❯{C.RESET} " if is_sel else "   "
                        color = C.BOLD if is_sel else C.RESET
                        uid_tag = f"[{r['uuid'][:8]}]"
                        date_str = r['date'][:11]
                        model_str = r.get("model", "-")[:13]
                        dur_str = r.get("duration", "-")[:7]
                        q_text = r.get("query", "")
                        q_disp = (q_text[:38] + "..") if len(q_text) > 38 else q_text
                        line = (
                            f"{prefix}⚪ {color}{uid_tag:<11}{C.RESET}{C.GRAY}{date_str:<13}{C.RESET}  "
                            f"{C.CYAN}{model_str:<14}{C.RESET}  "
                            f"{dur_str:<8}  "
                            f'\"{q_disp}\"'
                        )
                        buf.append(line)

                buf.append("")
                buf.append(f" {C.BOLD}[OPTIONS & BUTTONS]{C.RESET}")
                btn_start = rec_count
                for idx in range(btn_start, len(items)):
                    is_sel = (idx == selected_idx)
                    prefix = f" {C.CYAN}❯{C.RESET} " if is_sel else "   "
                    color = C.CYAN if is_sel else C.RESET
                    buf.append(f"{prefix}{color}{items[idx]['label']}{C.RESET}")

                buf.append(f"{C.GRAY}{'─' * 92}{C.RESET}")
                buf.append(f" {C.BOLD}Keys:{C.RESET} [↑/↓] Navigate  |  [Enter] Open  |  [d] Delete  |  [b] Back  |  [q] Quit")
                buf.append(f"{C.BOLD}{'=' * 92}{C.RESET}")

            # Rewind and erase previous frame in place, then draw clean buffer
            content = "\n".join(f"\r\033[2K{line}" for line in buf)
            if prev_lines > 0:
                sys.stdout.write(f"\r\033[{prev_lines}A\033[J")
            sys.stdout.write(content + "\n")
            sys.stdout.flush()
            prev_lines = len(buf)

            k = read_key()
            if k in ("\x1b[A", "w"):
                selected_idx = max(0, selected_idx - 1)
            elif k in ("\x1b[B", "s"):
                selected_idx = min(len(items) - 1, selected_idx + 1)
            elif k in ("\r", "\n"):
                sel_item = items[selected_idx]
                if sel_item["type"] == "active":
                    if prev_lines > 0:
                        sys.stdout.write(f"\r\033[{prev_lines}A\033[J")
                        sys.stdout.flush()
                        prev_lines = 0
                    sys.exit(stream_session(sel_item["id"]))
                elif sel_item["type"] in ("history", "full_history"):
                    if prev_lines > 0:
                        sys.stdout.write(f"\r\033[{prev_lines}A\033[J")
                        sys.stdout.flush()
                        prev_lines = 0
                    show_session(sel_item["id"])
                    prompt = f"{C.BOLD}[Enter/Space]{C.RESET} Return to explorer   {C.BOLD}[d]{C.RESET} Delete session   {C.BOLD}[q/Ctrl+C]{C.RESET} Quit"
                    action = wait_for_return(prompt)
                    if action == "delete":
                        full_id = sel_item["data"].get("full_id", sel_item["id"])
                        q_t = sel_item["data"].get("query", "")
                        if confirm_delete_prompt(sel_item["id"], q_t):
                            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                                delete_sessions([full_id], force=True)
                    elif action == "quit":
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        sys.exit(0)
                    continue
                elif sel_item["type"] == "switch_full":
                    view_mode = "full"
                    selected_idx = 0
                    scroll_offset = 0
                    continue
                elif sel_item["type"] == "switch_main":
                    view_mode = "main"
                    selected_idx = 0
                    scroll_offset = 0
                    continue
                elif sel_item["type"] == "quit":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    sys.exit(0)
            elif k in ("d", "D"):
                sel_item = items[selected_idx]
                if sel_item["type"] in ("history", "full_history"):
                    full_id = sel_item["data"].get("full_id", sel_item["id"])
                    q_t = sel_item["data"].get("query", "")
                    if confirm_delete_prompt(sel_item["id"], q_t):
                        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            delete_sessions([full_id], force=True)
                    continue
                elif sel_item["type"] == "active":
                    sys.stdout.write(f"\r\033[2K⚠️  Cannot delete active session. Press [k] to kill first.")
                    sys.stdout.flush()
                    time.sleep(0.9)
                    sys.stdout.write("\r\033[2K")
                    sys.stdout.flush()
            elif k in ("k", "K"):
                sel_item = items[selected_idx]
                if sel_item["type"] == "active":
                    kill_session(sel_item["id"])
                    time.sleep(0.3)
                    continue
            elif k in ("h", "H"):
                if view_mode != "full":
                    view_mode = "full"
                    selected_idx = 0
                    scroll_offset = 0
                continue
            elif k in ("b", "B", "\x1b"):
                if view_mode != "main":
                    view_mode = "main"
                    selected_idx = 0
                    scroll_offset = 0
                continue
            elif k in ("q", "Q", "\x03"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                sys.exit(0)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0


def main() -> None:
    try:
        args = sys.argv[1:]
        if not args:
            if sys.stdin.isatty() and sys.stdout.isatty():
                sys.exit(interactive_explorer())
            list_sessions()
            sys.exit(0)

        cmd = args[0].lower()
        if cmd in ("rm", "del", "delete"):
            targets = []
            force = False
            dry_run = False
            for a in args[1:]:
                if a in ("-f", "--force"):
                    force = True
                elif a in ("-n", "--dry-run"):
                    dry_run = True
                else:
                    targets.append(a)
            if not targets:
                print("Usage: asessions rm [-f] [-n] <session_id|#_index> [session_id...]")
                sys.exit(1)
            delete_sessions(targets, dry_run=dry_run, force=force)
            sys.exit(0)

        summary_flag = any(a in ("--summary", "-s", "summary") for a in args)
        target = next((a for a in args if not a.startswith("-") and a != "summary"), None)
        if not target:
            list_sessions()
            sys.exit(0)

        show_session(target, summary_only=summary_flag)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
