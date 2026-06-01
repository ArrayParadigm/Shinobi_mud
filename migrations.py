import logging

from content import create_authored_content_tables
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
            role_type INTEGER DEFAULT 0,
            health INTEGER DEFAULT 10,
            stamina INTEGER DEFAULT 10,
            chakra INTEGER DEFAULT 10,
            strength INTEGER DEFAULT 5,
            dexterity INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            wisdom INTEGER DEFAULT 5,
            dojo_alignment TEXT DEFAULT 'None'
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


MIGRATIONS = (
    (1, migration_001_non_admin_default),
    (2, migration_002_persistent_items),
    (3, migration_003_authored_content_and_npcs),
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
