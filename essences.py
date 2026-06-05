"""Veilborn essence definitions and compatibility helpers."""


ESSENCE_UNIMBUED = "Unimbued"

ESSENCE_TYPES = {
    "unimbued": {
        "name": ESSENCE_UNIMBUED,
        "stat_bonuses": {},
        "color": "white",
        "abilities": [],
    },
    "canine": {
        "name": "Canine",
        "stat_bonuses": {"strength": 1, "agility": 1},
        "color": "yellow",
        "abilities": ["scent-trail", "pack-instinct"],
    },
    "serpent": {
        "name": "Serpent",
        "stat_bonuses": {"dexterity": 1, "intelligence": 1},
        "color": "green",
        "abilities": ["shed-skin", "venom-sense"],
    },
    "ursine": {
        "name": "Ursine",
        "stat_bonuses": {"strength": 2},
        "color": "red",
        "abilities": ["iron-hide", "crushing-grip"],
    },
    "feline": {
        "name": "Feline",
        "stat_bonuses": {"agility": 2},
        "color": "magenta",
        "abilities": ["soft-step", "night-pounce"],
    },
}


def canonical_essence(value):
    """Return a known essence name, defaulting to Unimbued."""
    key = str(value or "").strip().casefold()
    for essence_key, definition in ESSENCE_TYPES.items():
        if key in {essence_key, definition["name"].casefold()}:
            return definition["name"]
    return ESSENCE_UNIMBUED


def compatible_for_lineage(first, second):
    """Unimbued is compatible with any essence; imbued partners match by essence."""
    first_name = canonical_essence(first)
    second_name = canonical_essence(second)
    return ESSENCE_UNIMBUED in {first_name, second_name} or first_name == second_name
