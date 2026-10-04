import json
from typing import Dict
from core.config import ROUTER_CONFIG_PATH

DEFAULT_TIERS: Dict[str, str] = {
    'cheap': 'auto',
    'balanced': 'auto',
    'smart': 'auto',
}

TIER_HINTS: Dict[str, str] = {
    'cheap': 'acheap',
    'balanced': 'abalanced',
    'smart': 'asmart',
}

TIER_MAP: Dict[str, str] = {
    'c': 'cheap',
    'ac': 'cheap',
    'cheap': 'cheap',
    'acheap': 'cheap',
    'b': 'balanced',
    'ab': 'balanced',
    'balanced': 'balanced',
    'abalanced': 'balanced',
    's': 'smart',
    'as': 'smart',
    'smart': 'smart',
    'asmart': 'smart',
}

def load_tier_config() -> Dict[str, str]:
    if ROUTER_CONFIG_PATH.exists():
        try:
            data = json.loads(ROUTER_CONFIG_PATH.read_text())
            for k, v in DEFAULT_TIERS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return DEFAULT_TIERS.copy()
    return DEFAULT_TIERS.copy()

def save_tier_config(config: Dict[str, str]) -> None:
    ROUTER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROUTER_CONFIG_PATH.write_text(json.dumps(config, indent=2) + '\n')
