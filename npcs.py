"""Persistent NPC templates, live instances, and lightweight combat."""


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


def attack_npc(cursor, username, x, y, npc_name):
    """Resolve one player attack and an immediate hostile counterattack."""
    player = cursor.execute(
        "SELECT id, health, max_health, strength FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}

    npc = cursor.execute(
        """
        SELECT npc_instances.id, npc_instances.health,
               npc_templates.name, npc_templates.behavior,
               npc_templates.attack_damage
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
        return {"status": "missing_target"}
    if npc["behavior"] != "hostile":
        return {"status": "not_attackable", "npc_name": npc["name"]}

    player_damage = max(1, player["strength"] // 2)
    npc_health = max(0, npc["health"] - player_damage)
    try:
        if npc_health == 0:
            cursor.execute(
                """
                UPDATE npc_instances
                SET health=0, defeated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (npc["id"],),
            )
            cursor.connection.commit()
            return {
                "status": "npc_defeated",
                "npc_name": npc["name"],
                "player_damage": player_damage,
            }

        cursor.execute(
            "UPDATE npc_instances SET health=? WHERE id=?",
            (npc_health, npc["id"]),
        )
        npc_damage = max(0, npc["attack_damage"])
        player_health = max(0, player["health"] - npc_damage)
        player_defeated = player_health == 0
        if player_defeated:
            player_health = player["max_health"]
        cursor.execute(
            "UPDATE players SET health=? WHERE id=?",
            (player_health, player["id"]),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise

    return {
        "status": "hit",
        "npc_name": npc["name"],
        "player_damage": player_damage,
        "npc_health": npc_health,
        "npc_damage": npc_damage,
        "player_health": player_health,
        "player_defeated": player_defeated,
    }


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
