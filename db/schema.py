"""Central schema entrypoints for fresh Veilborn databases."""

from character_state import create_character_state_tables
from expressions import create_technique_tables
from items import create_item_tables
from npcs import create_npc_tables
from socials import create_social_tables


def create_gameplay_tables(cursor):
    """Create gameplay tables that live outside the base player account table."""
    create_item_tables(cursor)
    create_npc_tables(cursor)
    create_technique_tables(cursor)
    create_social_tables(cursor)
    create_character_state_tables(cursor)
