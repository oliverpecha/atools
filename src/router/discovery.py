import subprocess
from typing import List, Tuple

VENDOR_ORDER: List[Tuple[str, List[str]]] = [
    ('ANTHROPIC', ['claude', 'sonnet', 'opus', 'haiku', 'fable']),
    ('OPENAI', ['gpt', 'o1', 'o3', 'o4']),
    ('GOOGLE', ['gemini', 'flash']),
    ('CURSOR & XAI', ['grok', 'composer', 'astra', 'auto']),
    ('OTHER', []),
]

def fetch_available_models() -> List[str]:
    raw_output = ''
    for cmd in (['agent', 'models'], ['agent', '--list-models']):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                raw_output = res.stdout
                break
        except Exception:
            continue

    discovered = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or 'available' in line.lower() or 'filter' in line.lower():
            continue
        parts = line.split()
        candidate = parts[0].lstrip('-*• ')
        if candidate:
            discovered.append(candidate)

    discovered = list(dict.fromkeys(discovered))
    if not discovered:
        discovered = [
            'auto',
            'claude-opus-5-thinking-high',
            'claude-fable-5-thinking-high',
            'claude-sonnet-5-thinking-high',
            'claude-3.7-sonnet',
            'claude-3.5-sonnet',
            'gpt-4o',
            'o3-mini',
            'gemini-2.5-flash',
            'gemini-2.5-pro',
            'grok-4.7',
            'composer-2.5',
        ]
    return discovered

def categorize_model(name: str) -> str:
    low = name.lower()
    for vendor, keys in VENDOR_ORDER[:-1]:
        if any(k in low for k in keys):
            return vendor
    return 'OTHER'
