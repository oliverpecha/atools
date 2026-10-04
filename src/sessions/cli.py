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

def main() -> None:
    args = sys.argv[1:]
    if not args:
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

if __name__ == "__main__":
    main()
