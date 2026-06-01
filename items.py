"""Persistent item definitions, room placements, and character inventories."""

from collections import Counter


def create_item_tables(cursor):
    """Create persistent item tables and their common lookup indexes."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS item_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS room_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_definition_id INTEGER NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            seed_key TEXT UNIQUE,
            FOREIGN KEY (item_definition_id) REFERENCES item_definitions(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_definition_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            seed_key TEXT,
            FOREIGN KEY (item_definition_id) REFERENCES item_definitions(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS room_items_location ON room_items (x, y)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS character_inventory_player ON character_inventory (player_id)"
    )


def ensure_item_seed_tracking(cursor):
    """Add seed provenance when upgrading Phase 9 inventory tables."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(character_inventory)")
    }
    if "seed_key" not in columns:
        cursor.execute("ALTER TABLE character_inventory ADD COLUMN seed_key TEXT")


def room_items(cursor, x, y):
    """Return item instances currently placed at a grid coordinate."""
    return cursor.execute(
        """
        SELECT room_items.id, item_definitions.name, item_definitions.description
        FROM room_items
        JOIN item_definitions ON item_definitions.id = room_items.item_definition_id
        WHERE room_items.x=? AND room_items.y=?
        ORDER BY item_definitions.name, room_items.id
        """,
        (x, y),
    ).fetchall()


def inventory_items(cursor, username):
    """Return item instances carried by a character."""
    return cursor.execute(
        """
        SELECT character_inventory.id, item_definitions.name, item_definitions.description
        FROM character_inventory
        JOIN item_definitions
          ON item_definitions.id = character_inventory.item_definition_id
        JOIN players ON players.id = character_inventory.player_id
        WHERE players.username=?
        ORDER BY item_definitions.name, character_inventory.id
        """,
        (username,),
    ).fetchall()


def format_item_names(items):
    """Format item rows as a concise sorted list with duplicate counts."""
    counts = Counter(item["name"] for item in items)
    return ", ".join(
        f"{name} x{count}" if count > 1 else name
        for name, count in sorted(counts.items(), key=lambda entry: entry[0].lower())
    )


def pickup_item(cursor, username, x, y, item_name):
    """Move one matching room item into a character inventory."""
    item = cursor.execute(
        """
        SELECT room_items.id, room_items.item_definition_id, room_items.seed_key,
               item_definitions.name
        FROM room_items
        JOIN item_definitions ON item_definitions.id = room_items.item_definition_id
        WHERE room_items.x=? AND room_items.y=?
          AND item_definitions.name=? COLLATE NOCASE
        ORDER BY room_items.id
        LIMIT 1
        """,
        (x, y, item_name),
    ).fetchone()
    if not item:
        return None

    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return None

    try:
        cursor.execute("DELETE FROM room_items WHERE id=?", (item["id"],))
        cursor.execute(
            """
            INSERT INTO character_inventory (item_definition_id, player_id, seed_key)
            VALUES (?, ?, ?)
            """,
            (item["item_definition_id"], player["id"], item["seed_key"]),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return item["name"]


def drop_item(cursor, username, x, y, item_name):
    """Move one matching inventory item onto the character's grid coordinate."""
    item = cursor.execute(
        """
        SELECT character_inventory.id,
               character_inventory.item_definition_id,
               character_inventory.seed_key,
               item_definitions.name
        FROM character_inventory
        JOIN item_definitions
          ON item_definitions.id = character_inventory.item_definition_id
        JOIN players ON players.id = character_inventory.player_id
        WHERE players.username=? AND item_definitions.name=? COLLATE NOCASE
        ORDER BY character_inventory.id
        LIMIT 1
        """,
        (username, item_name),
    ).fetchone()
    if not item:
        return None

    try:
        cursor.execute("DELETE FROM character_inventory WHERE id=?", (item["id"],))
        cursor.execute(
            """
            INSERT INTO room_items (item_definition_id, x, y, seed_key)
            VALUES (?, ?, ?, ?)
            """,
            (item["item_definition_id"], x, y, item["seed_key"]),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return item["name"]
