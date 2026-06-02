import logging

from content import create_authored_content_tables
from body import ensure_body_columns
from items import create_item_tables, ensure_item_seed_tracking
from npcs import create_npc_tables


PLAYER_COLUMNS = (
    "id",
    "username",
    "password",
    "x",
    "y",
    "is_admin",
    "role_type",
    "health",
    "stamina",
    "chakra",
    "strength",
    "dexterity",
    "agility",
    "intelligence",
    "wisdom",
    "dojo_alignment",
    "max_health",
    "max_stamina",
    "max_chakra",
    "clan",
    "natural_release",
    "nutrition",
    "hydration",
    "fatigue",
    "recovery_state",
)


def create_players_table(cursor, table_name="players"):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT NOT NULL,
            x INTEGER DEFAULT 500,
            y INTEGER DEFAULT 500,
            is_admin BOOLEAN DEFAULT 0,
            role_type TEXT DEFAULT 'newbie',
            health INTEGER DEFAULT 10,
            stamina INTEGER DEFAULT 10,
            chakra INTEGER DEFAULT 10,
            strength INTEGER DEFAULT 5,
            dexterity INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            wisdom INTEGER DEFAULT 5,
            dojo_alignment TEXT DEFAULT 'None',
            max_health INTEGER DEFAULT 10,
            max_stamina INTEGER DEFAULT 10,
            max_chakra INTEGER DEFAULT 10,
            clan TEXT DEFAULT 'Unaffiliated',
            natural_release TEXT DEFAULT 'Undeclared',
            nutrition INTEGER NOT NULL DEFAULT 100,
            hydration INTEGER NOT NULL DEFAULT 100,
            fatigue INTEGER NOT NULL DEFAULT 0,
            recovery_state TEXT NOT NULL DEFAULT 'ready'
        )
        """
    )


def migration_001_non_admin_default(cursor):
    """Rebuild legacy player tables so new accounts default to non-admin."""
    columns = cursor.execute("PRAGMA table_info(players)").fetchall()
    is_admin = next((column for column in columns if column[1] == "is_admin"), None)
    if is_admin and str(is_admin[4]).strip("'\"") == "0":
        return

    legacy_columns = {column[1] for column in columns}
    copied_columns = [column for column in PLAYER_COLUMNS if column in legacy_columns]

    cursor.execute("ALTER TABLE players RENAME TO players_legacy")
    create_players_table(cursor)
    if copied_columns:
        names = ", ".join(copied_columns)
        cursor.execute(f"INSERT INTO players ({names}) SELECT {names} FROM players_legacy")
    cursor.execute("DROP TABLE players_legacy")


def migration_002_persistent_items(cursor):
    """Add persistent room objects and character inventories."""
    create_item_tables(cursor)


def migration_003_authored_content_and_npcs(cursor):
    """Track authored imports and add persistent NPC state."""
    create_item_tables(cursor)
    ensure_item_seed_tracking(cursor)
    create_authored_content_tables(cursor)
    create_npc_tables(cursor)


def migration_004_npc_combat_state(cursor):
    """Add authored NPC combat tuning and live health state."""
    create_npc_tables(cursor)


def ensure_player_foundation_columns(cursor):
    """Add durable character identity and maximum resource fields."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    for column_name, definition in (
        ("max_health", "INTEGER DEFAULT 10"),
        ("max_stamina", "INTEGER DEFAULT 10"),
        ("max_chakra", "INTEGER DEFAULT 10"),
        ("clan", "TEXT DEFAULT 'Unaffiliated'"),
        ("natural_release", "TEXT DEFAULT 'Undeclared'"),
    ):
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {column_name} {definition}")
    cursor.execute("UPDATE players SET max_health=health WHERE max_health IS NULL OR max_health < health")
    cursor.execute("UPDATE players SET max_stamina=stamina WHERE max_stamina IS NULL OR max_stamina < stamina")
    cursor.execute("UPDATE players SET max_chakra=chakra WHERE max_chakra IS NULL OR max_chakra < chakra")
    if "role_type" in columns:
        cursor.execute(
            "UPDATE players SET role_type='newbie' "
            "WHERE role_type IS NULL OR role_type=0 OR role_type='0'"
        )
        cursor.execute("UPDATE players SET role_type='Ninjutsu' WHERE role_type='a'")
        cursor.execute("UPDATE players SET role_type='Genjutsu' WHERE role_type='b'")
        cursor.execute("UPDATE players SET role_type='Taijutsu' WHERE role_type='c'")


def migration_005_inventory_and_character_foundation(cursor):
    """Add item interaction metadata, equipment, and character identity."""
    create_item_tables(cursor)
    ensure_item_seed_tracking(cursor)
    ensure_player_foundation_columns(cursor)


def migration_006_combat_reliability(cursor):
    """Add authored NPC accuracy and evasion for stat-based combat."""
    create_npc_tables(cursor)


def migration_007_body_foundation(cursor):
    """Add abstract body resources for rest and future recovery systems."""
    ensure_body_columns(cursor)


def migration_008_consumable_items(cursor):
    """Add authored food and drink restoration metadata."""
    create_item_tables(cursor)


MIGRATIONS = (
    (1, migration_001_non_admin_default),
    (2, migration_002_persistent_items),
    (3, migration_003_authored_content_and_npcs),
    (4, migration_004_npc_combat_state),
    (5, migration_005_inventory_and_character_foundation),
    (6, migration_006_combat_reliability),
    (7, migration_007_body_foundation),
    (8, migration_008_consumable_items),
)


def apply_migrations(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row[0]
        for row in cursor.execute("SELECT version FROM schema_migrations").fetchall()
    }

    for version, migration in MIGRATIONS:
        if version in applied:
            continue
        logging.info("Applying database migration %s.", version)
        migration(cursor)
        cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    connection.commit()
