import os
from pathlib import Path

ROUTER_CONFIG_PATH = Path(
    os.environ.get("ATOOLS_CONFIG", os.path.expanduser("~/.cursor/arouter-config.json"))
)

TRANSCRIPTS_GLOB = "/root/.cursor/projects/*/agent-transcripts/*/*.jsonl"
CHATS_GLOB_BASE = "/root/.cursor/chats/*"
PROJECTS_TRANSCRIPTS_BASE = "/root/.cursor/projects/*/agent-transcripts"
