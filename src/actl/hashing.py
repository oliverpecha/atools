"""Content-addressed hashing helpers."""
from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from pathlib import Path
from typing import Any


def file_sha256(path: Path | str) -> str:
    p = Path(path)
    st = os.lstat(p)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ValueError(f"Not a regular file: {path}")
    return hashlib.sha256(p.read_bytes()).hexdigest().lower()


def manifest_sha256(directory: Path | str) -> str:
    root = Path(directory)
    st = os.lstat(root)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise ValueError(f"Not a non-symlink directory: {directory}")
    rows: list[tuple[bytes, bytes]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for entry in list(dirnames) + list(filenames):
            full_path = os.path.join(dirpath, entry)
            entry_stat = os.lstat(full_path)
            if stat.S_ISLNK(entry_stat.st_mode):
                raise ValueError(f"Symlink not allowed in manifest: {full_path}")
            if not (stat.S_ISDIR(entry_stat.st_mode) or stat.S_ISREG(entry_stat.st_mode)):
                raise ValueError(f"Special file not allowed in manifest: {full_path}")
            if stat.S_ISREG(entry_stat.st_mode):
                rel = os.path.relpath(full_path, root).replace(os.sep, "/")
                exec_flag = "x" if (entry_stat.st_mode & 0o111) != 0 else "-"
                digest = hashlib.sha256(Path(full_path).read_bytes()).hexdigest().lower()
                rows.append(
                    (rel.encode("utf-8"), f"{rel}\0{exec_flag}\0{digest}\n".encode("utf-8"))
                )
    rows.sort(key=lambda r: r[0])
    joined = b"".join(r[1] for r in rows)
    return hashlib.sha256(joined).hexdigest().lower()


def _validate_canonical(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError("Dictionary keys must be strings")
            _validate_canonical(v)
    elif isinstance(obj, list):
        for v in obj:
            _validate_canonical(v)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("NaN/Infinity not allowed")
    elif isinstance(obj, str):
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in obj):
            raise ValueError("Surrogates not allowed")


def canonical_json(obj: Any) -> bytes:
    _validate_canonical(obj)
    s = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return s.encode("utf-8")


def json_sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest().lower()
