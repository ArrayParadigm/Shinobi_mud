"""Persistent item definitions, room placements, inventories, and equipment."""

from collections import Counter
import re


def create_item_tables(cursor):
    """Create persistent item tables and their common lookup indexes."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS item_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            keywords TEXT NOT NULL DEFAULT '',
            item_type TEXT NOT NULL DEFAULT 'misc',
            equipment_slot TEXT,
            use_text TEXT NOT NULL DEFAULT '',
            damage_bonus INTEGER NOT NULL DEFAULT 0,
            throw_damage INTEGER NOT NULL DEFAULT 0,
            nutrition_restore INTEGER NOT NULL DEFAULT 0,
            hydration_restore INTEGER NOT NULL DEFAULT 0
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
            equipped_slot TEXT,
            FOREIGN KEY (item_definition_id) REFERENCES item_definitions(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS room_items_location ON room_items (x, y)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS character_inventory_player ON character_inventory (player_id)"
    )
    ensure_item_metadata(cursor)


def ensure_item_seed_tracking(cursor):
    """Add seed provenance when upgrading Phase 9 inventory tables."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(character_inventory)")
    }
    if "seed_key" not in columns:
        cursor.execute("ALTER TABLE character_inventory ADD COLUMN seed_key TEXT")


def ensure_item_metadata(cursor):
    """Add authored item details and live equipment state to older tables."""
    definition_columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(item_definitions)")
    }
    for column_name, definition in (
        ("keywords", "TEXT NOT NULL DEFAULT ''"),
        ("item_type", "TEXT NOT NULL DEFAULT 'misc'"),
        ("equipment_slot", "TEXT"),
        ("use_text", "TEXT NOT NULL DEFAULT ''"),
        ("damage_bonus", "INTEGER NOT NULL DEFAULT 0"),
        ("throw_damage", "INTEGER NOT NULL DEFAULT 0"),
        ("nutrition_restore", "INTEGER NOT NULL DEFAULT 0"),
        ("hydration_restore", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if column_name not in definition_columns:
            cursor.execute(f"ALTER TABLE item_definitions ADD COLUMN {column_name} {definition}")

    inventory_columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(character_inventory)")
    }
    if "equipped_slot" not in inventory_columns:
        cursor.execute("ALTER TABLE character_inventory ADD COLUMN equipped_slot TEXT")


def room_items(cursor, x, y):
    """Return item instances currently placed at a grid coordinate."""
    return cursor.execute(
        """
        SELECT room_items.id, item_definitions.name, item_definitions.description,
               item_definitions.keywords, item_definitions.item_type,
               item_definitions.equipment_slot, item_definitions.use_text,
               item_definitions.damage_bonus, item_definitions.throw_damage,
               item_definitions.nutrition_restore,
               item_definitions.hydration_restore
        FROM room_items
        JOIN item_definitions ON item_definitions.id = room_items.item_definition_id
        WHERE room_items.x=? AND room_items.y=?
        ORDER BY room_items.id
        """,
        (x, y),
    ).fetchall()


def inventory_items(cursor, username):
    """Return item instances carried by a character."""
    return cursor.execute(
        """
        SELECT character_inventory.id, character_inventory.item_definition_id,
               character_inventory.seed_key,
               item_definitions.name, item_definitions.description,
               item_definitions.keywords, item_definitions.item_type,
               item_definitions.equipment_slot, item_definitions.use_text,
               item_definitions.damage_bonus, item_definitions.throw_damage,
               item_definitions.nutrition_restore,
               item_definitions.hydration_restore, character_inventory.equipped_slot
        FROM character_inventory
        JOIN item_definitions
          ON item_definitions.id = character_inventory.item_definition_id
        JOIN players ON players.id = character_inventory.player_id
        WHERE players.username=?
        ORDER BY character_inventory.id
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


def format_inventory(items):
    """Format carried and equipped items as readable inventory lines."""
    equipped = [item for item in items if item["equipped_slot"]]
    carried = [item for item in items if not item["equipped_slot"]]
    return [
        f"  Carried: {format_item_names(carried) if carried else 'None'}",
        (
            "  Equipped: "
            + (
                ", ".join(
                    f'{item["equipped_slot"]}: {item["name"]}'
                    for item in equipped
                )
                if equipped
                else "None"
            )
        ),
    ]


def resolve_item(items, target):
    """Resolve exact, keyword, and prefix item targets with optional ordinals."""
    match = re.fullmatch(r"(?:(\d+)\.)?(.+)", target.strip())
    if not match:
        return None
    ordinal = int(match.group(1) or 1)
    query = match.group(2).strip().casefold()
    if ordinal < 1 or not query:
        return None

    exact = [item for item in items if item["name"].casefold() == query]
    matches = exact or [item for item in items if _matches_item(item, query)]
    return matches[ordinal - 1] if len(matches) >= ordinal else None


def _matches_item(item, query):
    searchable = [item["name"], *(item["keywords"] or "").split()]
    return any(query in value.casefold() for value in searchable)


def pickup_item(cursor, username, x, y, item_name):
    """Move one matching room item into a character inventory."""
    visible_items = cursor.execute(
        """
        SELECT room_items.id, room_items.item_definition_id, room_items.seed_key,
               item_definitions.name, item_definitions.keywords
        FROM room_items
        JOIN item_definitions ON item_definitions.id = room_items.item_definition_id
        WHERE room_items.x=? AND room_items.y=?
        ORDER BY room_items.id
        """,
        (x, y),
    ).fetchall()
    item = resolve_item(visible_items, item_name)
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
    carried_items = cursor.execute(
        """
        SELECT character_inventory.id,
               character_inventory.item_definition_id,
               character_inventory.seed_key,
               item_definitions.name,
               item_definitions.keywords
        FROM character_inventory
        JOIN item_definitions
          ON item_definitions.id = character_inventory.item_definition_id
        JOIN players ON players.id = character_inventory.player_id
        WHERE players.username=?
        ORDER BY character_inventory.id
        """,
        (username,),
    ).fetchall()
    item = resolve_item(carried_items, item_name)
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


def examine_item(cursor, username, x, y, item_name):
    """Return one matching visible or carried item for inspection."""
    item = resolve_item(room_items(cursor, x, y), item_name)
    if item:
        return item
    return resolve_item(inventory_items(cursor, username), item_name)


def wield_item(cursor, username, item_name):
    """Equip one carried item in its authored slot."""
    item = resolve_item(inventory_items(cursor, username), item_name)
    if not item:
        return {"status": "missing"}
    if not item["equipment_slot"]:
        return {"status": "not_equippable", "name": item["name"]}

    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    try:
        cursor.execute(
            "UPDATE character_inventory SET equipped_slot=NULL WHERE player_id=? AND equipped_slot=?",
            (player["id"], item["equipment_slot"]),
        )
        cursor.execute(
            "UPDATE character_inventory SET equipped_slot=? WHERE id=?",
            (item["equipment_slot"], item["id"]),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return {"status": "equipped", "name": item["name"], "slot": item["equipment_slot"]}


def remove_item(cursor, username, item_name):
    """Unequip one carried item while leaving it in inventory."""
    item = resolve_item(inventory_items(cursor, username), item_name)
    if not item:
        return {"status": "missing"}
    if not item["equipped_slot"]:
        return {"status": "not_equipped", "name": item["name"]}

    cursor.execute(
        "UPDATE character_inventory SET equipped_slot=NULL WHERE id=?",
        (item["id"],),
    )
    cursor.connection.commit()
    return {"status": "removed", "name": item["name"]}


def consume_item(cursor, username, item_name, expected_type, resource_name):
    """Consume one carried item and restore one bounded body resource."""
    item = resolve_item(inventory_items(cursor, username), item_name)
    if not item:
        return {"status": "missing"}
    if item["item_type"] != expected_type:
        return {"status": "wrong_type", "name": item["name"]}

    restore_amount = item[f"{resource_name}_restore"]
    player = cursor.execute(
        f"SELECT {resource_name} FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}
    if player[resource_name] >= 100:
        return {"status": "full", "name": item["name"]}

    restored = min(100, player[resource_name] + restore_amount)
    try:
        cursor.execute("DELETE FROM character_inventory WHERE id=?", (item["id"],))
        cursor.execute(
            f"UPDATE players SET {resource_name}=? WHERE username=?",
            (restored, username),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return {
        "status": "consumed",
        "name": item["name"],
        "resource": restored,
        "restored": restored - player[resource_name],
    }
