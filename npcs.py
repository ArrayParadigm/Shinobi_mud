"""Persistent NPC templates, live instances, and lightweight combat."""

import random

from body import add_fatigue
from items import inventory_items, resolve_item
from techniques import consume_substitution, record_skill_use


BASE_HIT_CHANCE = 50
STAT_HIT_CHANCE_STEP = 5
MIN_HIT_CHANCE = 5
MAX_HIT_CHANCE = 95


def create_npc_tables(cursor):
    """Create persistent NPC template and spawned-instance tables."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS npc_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            dialogue TEXT NOT NULL,
            behavior TEXT NOT NULL DEFAULT 'static',
            max_health INTEGER NOT NULL DEFAULT 1,
            attack_damage INTEGER NOT NULL DEFAULT 0,
            accuracy INTEGER NOT NULL DEFAULT 5,
            evasion INTEGER NOT NULL DEFAULT 5,
            respawn_seconds INTEGER NOT NULL DEFAULT 60
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS npc_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            npc_template_id INTEGER NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            home_x INTEGER NOT NULL,
            home_y INTEGER NOT NULL,
            seed_key TEXT UNIQUE,
            last_tick_at TEXT,
            health INTEGER NOT NULL DEFAULT 1,
            defeated_at TEXT,
            FOREIGN KEY (npc_template_id) REFERENCES npc_templates(id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS npc_instances_location ON npc_instances (x, y)")
    ensure_npc_combat_columns(cursor)


def ensure_npc_combat_columns(cursor):
    """Add Phase 11 combat state when upgrading existing NPC tables."""
    template_columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(npc_templates)")
    }
    for column_name, definition in (
        ("max_health", "INTEGER NOT NULL DEFAULT 1"),
        ("attack_damage", "INTEGER NOT NULL DEFAULT 0"),
        ("accuracy", "INTEGER NOT NULL DEFAULT 5"),
        ("evasion", "INTEGER NOT NULL DEFAULT 5"),
        ("respawn_seconds", "INTEGER NOT NULL DEFAULT 60"),
    ):
        if column_name not in template_columns:
            cursor.execute(f"ALTER TABLE npc_templates ADD COLUMN {column_name} {definition}")

    instance_columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(npc_instances)")
    }
    for column_name, definition in (
        ("health", "INTEGER NOT NULL DEFAULT 1"),
        ("defeated_at", "TEXT"),
    ):
        if column_name not in instance_columns:
            cursor.execute(f"ALTER TABLE npc_instances ADD COLUMN {column_name} {definition}")


def npcs_at(cursor, x, y):
    """Return NPC instances at a grid coordinate."""
    return cursor.execute(
        """
        SELECT npc_instances.id, npc_templates.name, npc_templates.description,
               npc_templates.dialogue, npc_templates.behavior
        FROM npc_instances
        JOIN npc_templates ON npc_templates.id = npc_instances.npc_template_id
        WHERE npc_instances.x=? AND npc_instances.y=? AND npc_instances.health > 0
        ORDER BY npc_templates.name, npc_instances.id
        """,
        (x, y),
    ).fetchall()


def talk_to_npc(cursor, x, y, npc_name):
    """Return dialogue for one NPC at a location."""
    return cursor.execute(
        """
        SELECT npc_templates.name, npc_templates.dialogue
        FROM npc_instances
        JOIN npc_templates ON npc_templates.id = npc_instances.npc_template_id
        WHERE npc_instances.x=? AND npc_instances.y=?
          AND npc_instances.health > 0
          AND npc_templates.name=? COLLATE NOCASE
        ORDER BY npc_instances.id
        LIMIT 1
        """,
        (x, y, npc_name),
    ).fetchone()


def consider_npc(cursor, x, y, npc_name):
    """Return visible NPC combat details for player inspection."""
    return cursor.execute(
        """
        SELECT npc_templates.name, npc_templates.description,
               npc_templates.behavior, npc_instances.health,
               npc_templates.max_health, npc_templates.attack_damage,
               npc_templates.accuracy, npc_templates.evasion
        FROM npc_instances
        JOIN npc_templates ON npc_templates.id = npc_instances.npc_template_id
        WHERE npc_instances.x=? AND npc_instances.y=?
          AND npc_instances.health > 0
          AND npc_templates.name=? COLLATE NOCASE
        ORDER BY npc_instances.id
        LIMIT 1
        """,
        (x, y, npc_name),
    ).fetchone()


def hit_chance(attacker_accuracy, defender_evasion):
    """Return a bounded percentage chance to land one combat action."""
    chance = BASE_HIT_CHANCE + (
        int(attacker_accuracy) - int(defender_evasion)
    ) * STAT_HIT_CHANCE_STEP
    return max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, chance))


def _equipped_damage_bonus(cursor, player_id):
    return cursor.execute(
        """
        SELECT COALESCE(SUM(item_definitions.damage_bonus), 0)
        FROM character_inventory
        JOIN item_definitions
          ON item_definitions.id=character_inventory.item_definition_id
        WHERE character_inventory.player_id=?
          AND character_inventory.equipped_slot IS NOT NULL
        """,
        (player_id,),
    ).fetchone()[0]


def attack_npc(cursor, username, x, y, npc_name):
    """Resolve one locked melee turn and an immediate hostile counterattack."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            """
            SELECT id, health, max_health, strength, dexterity, agility
            FROM players
            WHERE username=?
            """,
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}

        npc = cursor.execute(
            """
            SELECT npc_instances.id, npc_instances.health,
                   npc_templates.name, npc_templates.behavior,
                   npc_templates.attack_damage, npc_templates.accuracy,
                   npc_templates.evasion
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id = npc_instances.npc_template_id
            WHERE npc_instances.x=? AND npc_instances.y=?
              AND npc_instances.health > 0
              AND npc_templates.name=? COLLATE NOCASE
            ORDER BY npc_instances.id
            LIMIT 1
            """,
            (x, y, npc_name),
        ).fetchone()
        if not npc:
            connection.rollback()
            return {"status": "missing_target"}
        if npc["behavior"] != "hostile":
            connection.rollback()
            return {"status": "not_attackable", "npc_name": npc["name"]}

        add_fatigue(cursor, username, 5)
        weapon_damage = _equipped_damage_bonus(cursor, player["id"])
        player_damage = max(1, player["strength"] // 2 + weapon_damage)
        player_hit_chance = hit_chance(player["dexterity"], npc["evasion"])
        player_hit = random.randint(1, 100) <= player_hit_chance
        npc_health = npc["health"]
        if player_hit:
            npc_health = max(0, npc_health - player_damage)
        if npc_health == 0:
            cursor.execute(
                """
                UPDATE npc_instances
                SET health=0, defeated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (npc["id"],),
            )
            connection.commit()
            return {
                "status": "npc_defeated",
                "npc_name": npc["name"],
                "player_damage": player_damage,
                "weapon_damage": weapon_damage,
                "player_hit_chance": player_hit_chance,
            }

        if player_hit:
            cursor.execute(
                "UPDATE npc_instances SET health=? WHERE id=?",
                (npc_health, npc["id"]),
            )
        npc_damage = max(0, npc["attack_damage"])
        npc_hit_chance = hit_chance(npc["accuracy"], player["agility"])
        npc_hit = random.randint(1, 100) <= npc_hit_chance
        player_health = player["health"]
        substitution = consume_substitution(cursor, username) if npc_hit else None
        if npc_hit and not substitution:
            player_health = max(0, player_health - npc_damage)
        player_defeated = player_health == 0
        if player_defeated:
            player_health = player["max_health"]
        if npc_hit and not substitution:
            cursor.execute(
                "UPDATE players SET health=? WHERE id=?",
                (player_health, player["id"]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "status": "exchange",
        "npc_name": npc["name"],
        "player_hit": player_hit,
        "player_hit_chance": player_hit_chance,
        "player_damage": player_damage,
        "weapon_damage": weapon_damage,
        "npc_health": npc_health,
        "npc_hit": npc_hit,
        "npc_hit_chance": npc_hit_chance,
        "npc_damage": npc_damage,
        "player_health": player_health,
        "player_defeated": player_defeated,
        "substitution": substitution,
    }


def throw_item_at_npc(cursor, username, x, y, item_name, npc_name):
    """Throw one carried authored item at a hostile NPC within one grid step."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            "SELECT id, dexterity FROM players WHERE username=?",
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}

        item = resolve_item(inventory_items(cursor, username), item_name)
        if not item:
            connection.rollback()
            return {"status": "missing_item"}
        if item["throw_damage"] <= 0:
            connection.rollback()
            return {"status": "not_throwable", "item_name": item["name"]}

        nearby_npcs = cursor.execute(
            """
            SELECT npc_instances.id, npc_instances.x, npc_instances.y,
                   npc_instances.health, npc_templates.name,
                   npc_templates.behavior, npc_templates.evasion
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_instances.health > 0
              AND ABS(npc_instances.x - ?) + ABS(npc_instances.y - ?) <= 1
            ORDER BY npc_instances.id
            """,
            (x, y),
        ).fetchall()
        npc = _resolve_named_npc(nearby_npcs, npc_name)
        if not npc:
            connection.rollback()
            return {"status": "missing_target"}
        if npc["behavior"] != "hostile":
            connection.rollback()
            return {"status": "not_attackable", "npc_name": npc["name"]}

        add_fatigue(cursor, username, 2)
        player_hit_chance = hit_chance(player["dexterity"], npc["evasion"])
        player_hit = random.randint(1, 100) <= player_hit_chance
        npc_health = npc["health"]
        if player_hit:
            npc_health = max(0, npc_health - item["throw_damage"])

        cursor.execute("DELETE FROM character_inventory WHERE id=?", (item["id"],))
        cursor.execute(
            """
            INSERT INTO room_items (item_definition_id, x, y, seed_key)
            VALUES (?, ?, ?, ?)
            """,
            (item["item_definition_id"], npc["x"], npc["y"], item["seed_key"]),
        )
        if npc_health == 0:
            cursor.execute(
                """
                UPDATE npc_instances
                SET health=0, defeated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (npc["id"],),
            )
        elif player_hit:
            cursor.execute(
                "UPDATE npc_instances SET health=? WHERE id=?",
                (npc_health, npc["id"]),
            )
        progress = record_skill_use(cursor, username, "throw", commit=False)
        if progress["status"] != "recorded":
            raise RuntimeError("Throw skill progression is unavailable.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "npc_defeated" if npc_health == 0 else "thrown",
        "item_name": item["name"],
        "npc_name": npc["name"],
        "player_hit": player_hit,
        "player_hit_chance": player_hit_chance,
        "player_damage": item["throw_damage"],
        "npc_health": npc_health,
        "progress_percent": progress["progress_percent"],
        "proficiency": progress["proficiency"],
    }


def _resolve_named_npc(npcs, target):
    query = target.strip().casefold()
    if not query:
        return None
    exact = [npc for npc in npcs if npc["name"].casefold() == query]
    matches = exact or [
        npc
        for npc in npcs
        if npc["name"].casefold().startswith(query)
    ]
    return matches[0] if len(matches) == 1 else None


def tick_npcs(connection):
    """Update timestamps and recover NPCs whose authored delay has elapsed."""
    connection.execute(
        """
        UPDATE npc_instances
        SET health=(
                SELECT max_health
                FROM npc_templates
                WHERE npc_templates.id=npc_instances.npc_template_id
            ),
            defeated_at=NULL
        WHERE health <= 0
          AND defeated_at IS NOT NULL
          AND datetime(
                defeated_at,
                '+' || (
                    SELECT respawn_seconds
                    FROM npc_templates
                    WHERE npc_templates.id=npc_instances.npc_template_id
                ) || ' seconds'
            ) <= CURRENT_TIMESTAMP
        """
    )
    cursor = connection.execute(
        "UPDATE npc_instances SET last_tick_at=CURRENT_TIMESTAMP"
    )
    connection.commit()
    return cursor.rowcount
