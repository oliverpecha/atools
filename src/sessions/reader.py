import os
import json
import glob
import re
import datetime
import sqlite3
from typing import Dict, Any

def parse_embedded_timestamp(raw_str: str):
    if not raw_str:
        return None
    raw_clean = re.sub(r"\(UTC\)", "", raw_str, flags=re.I).strip()
    try:
        return datetime.datetime.fromisoformat(raw_clean.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in (
        "%A, %b %d, %Y, %I:%M %p",
        "%A, %B %d, %Y, %I:%M %p",
        "%a, %b %d, %Y, %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            return datetime.datetime.strptime(raw_clean, fmt).replace(tzinfo=datetime.timezone.utc)
        except Exception:
            pass
    return None

def format_pretty_utc(ms) -> str:
    if not ms:
        return "N/A"
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%a, %b %d, %Y · %H:%M:%S UTC") if dt.second > 0 else dt.strftime("%a, %b %d, %Y · %H:%M UTC")

def format_table_utc(ms) -> str:
    if not ms:
        return "N/A"
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%b %d, %Y · %H:%M UTC")

def clean_text(raw) -> str:
    while isinstance(raw, (dict, list)):
        if isinstance(raw, dict):
            raw = raw.get("content", raw.get("text", raw.get("message", "")))
        elif isinstance(raw, list):
            raw = "\n".join(str(b.get("text", b.get("content", b))) if isinstance(b, dict) else str(b) for b in raw)
    raw = str(raw or "")
    raw = re.sub(r"<timestamp>.*?</timestamp>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"</?user_query>", "", raw)
    if "Context / Input:" in raw:
        raw = raw.split("Context / Input:")[0]
    return raw.strip()

def get_session_meta(uuid_str: str) -> Dict[str, Any]:
    meta = {
        "model": "gemini-3.8-flash",
        "title": "N/A",
        "duration": "N/A",
        "created_ms": None,
        "updated_ms": None,
        "created_utc": "N/A",
        "updated_utc": "N/A",
        "cwd": "unknown",
        "approval_mode": "default"
    }
    chats = glob.glob(f"/root/.cursor/chats/*/*{uuid_str}*")
    if not chats:
        return meta
    cdir = chats[0]

    meta_json = os.path.join(cdir, "meta.json")
    if os.path.exists(meta_json):
        try:
            with open(meta_json, "r", encoding="utf-8") as f:
                d = json.load(f)
                meta["created_ms"] = d.get("createdAtMs")
                meta["updated_ms"] = d.get("updatedAtMs")
                meta["created_utc"] = format_pretty_utc(meta["created_ms"])
                meta["updated_utc"] = format_pretty_utc(meta["updated_ms"])
                meta["cwd"] = d.get("cwd", meta["cwd"])
                meta["title"] = d.get("title", meta["title"])
                if meta["created_ms"] and meta["updated_ms"] and meta["updated_ms"] >= meta["created_ms"]:
                    sec = int((meta["updated_ms"] - meta["created_ms"]) / 1000)
                    meta["duration"] = f"{sec // 60}m {sec % 60:02d}s"
        except Exception:
            pass

    store_db = os.path.join(cdir, "store.db")
    if os.path.exists(store_db):
        try:
            conn = sqlite3.connect(store_db)
            row = conn.cursor().execute("SELECT * FROM meta LIMIT 1;").fetchone()
            conn.close()
            if row:
                for col in row:
                    raw = col if isinstance(col, str) else ""
                    if raw.startswith("7b") or raw.startswith("7B"):
                        try:
                            raw = bytes.fromhex(raw).decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                    if "lastUsedModel" in raw:
                        parsed = json.loads(raw)
                        meta["model"] = parsed.get("lastUsedModel", meta["model"])
                        meta["approval_mode"] = parsed.get("approvalMode", meta["approval_mode"])
                        if "name" in parsed and meta["title"] == "N/A":
                            meta["title"] = parsed.get("name")
                        break
        except Exception:
            pass
    return meta

def enrich_meta_from_transcript(meta: dict, fpath: str) -> dict:
    if not fpath or not os.path.exists(fpath):
        return meta
    try:
        timestamps = []
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                m = re.search(r"<timestamp>(.*?)</timestamp>", line)
                if m:
                    dt = parse_embedded_timestamp(m.group(1))
                    if dt:
                        timestamps.append(dt)
        stat = os.stat(fpath)
        file_mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc)
        file_ctime = datetime.datetime.fromtimestamp(stat.st_ctime, tz=datetime.timezone.utc)

        start_dt = timestamps[0] if timestamps else file_ctime
        end_dt = timestamps[-1] if len(timestamps) > 1 else file_mtime
        if end_dt < start_dt:
            end_dt = file_mtime

        if (not meta.get("created_utc") or meta["created_utc"] == "N/A") and start_dt:
            meta["created_utc"] = start_dt.strftime("%a, %b %d, %Y · %H:%M UTC")
            meta["created_ms"] = int(start_dt.timestamp() * 1000)

        if (not meta.get("updated_utc") or meta["updated_utc"] == "N/A") and end_dt:
            meta["updated_utc"] = end_dt.strftime("%a, %b %d, %Y · %H:%M UTC")
            meta["updated_ms"] = int(end_dt.timestamp() * 1000)

        if (not meta.get("duration") or meta["duration"] == "N/A") and start_dt and end_dt and end_dt >= start_dt:
            sec = int((end_dt - start_dt).total_seconds())
            meta["duration"] = f"{sec // 60}m {sec % 60:02d}s"
    except Exception:
        pass
    return meta
