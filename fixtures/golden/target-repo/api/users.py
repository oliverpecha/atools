# Authored-by: Perplexity (AI assistant by Perplexity AI), model family: Perplexity
"""In-memory user store. Schema is LOCKED (spec-001 'Locked')."""

USERS = {
    1: {"id": 1, "name": "Ada Lovelace", "email": "ada@example.test",
        "bio": "Mathematician", "avatar": "https://img.example.test/ada.png",
        "photos": ["a1", "a2", "a3"]},
    2: {"id": 2, "name": "Grace Hopper", "email": "grace@example.test",
        "bio": "Compiler pioneer", "avatar": "https://img.example.test/grace.png",
        "photos": ["g1", "g2", "g3", "g4", "g5"]},
    3: {"id": 3, "name": "Linus Private", "email": "linus@example.test",
        "bio": "Keeps to himself", "avatar": "https://img.example.test/linus.png",
        "photos": ["l1"]},
}


def get_user(user_id):
    """Return the user dict or None when unknown."""
    return USERS.get(user_id)


def list_user_ids():
    return sorted(USERS)
