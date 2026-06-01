"""Persistent NPC templates, instances, and lightweight updates."""


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
            behavior TEXT NOT NULL DEFAULT 'static'
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
            FOREIGN KEY (npc_template_id) REFERENCES npc_templates(id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS npc_instances_location ON npc_instances (x, y)")


def npcs_at(cursor, x, y):
    """Return NPC instances at a grid coordinate."""
    return cursor.execute(
        """
        SELECT npc_instances.id, npc_templates.name, npc_templates.description,
               npc_templates.dialogue, npc_templates.behavior
        FROM npc_instances
        JOIN npc_templates ON npc_templates.id = npc_instances.npc_template_id
        WHERE npc_instances.x=? AND npc_instances.y=?
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
          AND npc_templates.name=? COLLATE NOCASE
        ORDER BY npc_instances.id
        LIMIT 1
        """,
        (x, y, npc_name),
    ).fetchone()


def tick_npcs(connection):
    """Apply the minimal persistent NPC update for the current world tick."""
    cursor = connection.execute(
        "UPDATE npc_instances SET last_tick_at=CURRENT_TIMESTAMP"
    )
    connection.commit()
    return cursor.rowcount
