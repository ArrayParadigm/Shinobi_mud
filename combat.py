"""Persistent pulse combat engagements, stances, and queued techniques."""

import random

from body import add_fatigue
from npcs import _equipped_damage_bonus, _resolve_named_npc, hit_chance
from techniques import consume_substitution


BASE_AUTO_ATTACK_SECONDS = 6
BASE_AUTO_ATTACK_RANGE = 0
BALANCED_STANCE_NAME = "S3 - Balance"


def create_combat_tables(cursor):
    """Create persisted combat engagements, stances, and queued modifiers."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stance_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stance_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            accuracy_bonus INTEGER NOT NULL DEFAULT 0,
            evasion_bonus INTEGER NOT NULL DEFAULT 0,
            damage_bonus INTEGER NOT NULL DEFAULT 0,
            damage_reduction_bonus INTEGER NOT NULL DEFAULT 0,
            pulse_seconds INTEGER NOT NULL DEFAULT 6
        )
        """
    )
    ensure_stance_columns(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_stances (
            player_id INTEGER PRIMARY KEY,
            stance_definition_id INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (stance_definition_id) REFERENCES stance_definitions(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS combat_engagements (
            player_id INTEGER PRIMARY KEY,
            npc_instance_id INTEGER NOT NULL,
            next_pulse_at TEXT NOT NULL,
            engaged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS combat_action_queue (
            player_id INTEGER PRIMARY KEY,
            action_key TEXT NOT NULL,
            accuracy_bonus INTEGER NOT NULL DEFAULT 0,
            damage_bonus INTEGER NOT NULL DEFAULT 0,
            max_range INTEGER NOT NULL DEFAULT 0,
            status_key TEXT,
            evasion_bonus INTEGER NOT NULL DEFAULT 0,
            damage_reduction_bonus INTEGER NOT NULL DEFAULT 0,
            skip_attack INTEGER NOT NULL DEFAULT 0,
            stamina_restore INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
        """
    )
    ensure_combat_action_queue_columns(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS combat_technique_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technique_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            stamina_cost INTEGER NOT NULL DEFAULT 0,
            accuracy_bonus INTEGER NOT NULL DEFAULT 0,
            damage_bonus INTEGER NOT NULL DEFAULT 0,
            evasion_bonus INTEGER NOT NULL DEFAULT 0,
            damage_reduction_bonus INTEGER NOT NULL DEFAULT 0,
            max_range INTEGER NOT NULL DEFAULT 0,
            skip_attack INTEGER NOT NULL DEFAULT 0,
            stamina_restore INTEGER NOT NULL DEFAULT 0,
            is_available INTEGER NOT NULL DEFAULT 1
        )
        """
    )


def sync_stance_templates(cursor, templates):
    """Synchronize authored stance definitions without touching player choices."""
    for template in templates:
        cursor.execute(
            """
            INSERT INTO stance_definitions (
                stance_key, name, description, accuracy_bonus,
                evasion_bonus, damage_bonus, damage_reduction_bonus, pulse_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stance_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                accuracy_bonus=excluded.accuracy_bonus,
                evasion_bonus=excluded.evasion_bonus,
                damage_bonus=excluded.damage_bonus,
                damage_reduction_bonus=excluded.damage_reduction_bonus,
                pulse_seconds=excluded.pulse_seconds
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                int(template.get("accuracy_bonus", 0)),
                int(template.get("evasion_bonus", 0)),
                int(template.get("damage_bonus", 0)),
                int(template.get("damage_reduction_bonus", 0)),
                max(1, int(template.get("pulse_seconds", BASE_AUTO_ATTACK_SECONDS))),
            ),
        )


def ensure_stance_columns(cursor):
    """Add stance fields introduced after the initial pulse-combat schema."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(stance_definitions)")
    }
    if "damage_reduction_bonus" not in columns:
        cursor.execute(
            "ALTER TABLE stance_definitions "
            "ADD COLUMN damage_reduction_bonus INTEGER NOT NULL DEFAULT 0"
        )


def ensure_combat_action_queue_columns(cursor):
    """Add one-shot technique fields to the persisted combat queue."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(combat_action_queue)")
    }
    for column_name, definition in (
        ("evasion_bonus", "INTEGER NOT NULL DEFAULT 0"),
        ("damage_reduction_bonus", "INTEGER NOT NULL DEFAULT 0"),
        ("skip_attack", "INTEGER NOT NULL DEFAULT 0"),
        ("stamina_restore", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE combat_action_queue ADD COLUMN {column_name} {definition}")


def sync_combat_technique_templates(cursor, templates):
    """Synchronize authored pulse technique definitions."""
    create_combat_tables(cursor)
    for template in templates:
        cursor.execute(
            """
            INSERT INTO combat_technique_definitions (
                technique_key, name, description, stamina_cost,
                accuracy_bonus, damage_bonus, evasion_bonus,
                damage_reduction_bonus, max_range, skip_attack,
                stamina_restore, is_available
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(technique_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                stamina_cost=excluded.stamina_cost,
                accuracy_bonus=excluded.accuracy_bonus,
                damage_bonus=excluded.damage_bonus,
                evasion_bonus=excluded.evasion_bonus,
                damage_reduction_bonus=excluded.damage_reduction_bonus,
                max_range=excluded.max_range,
                skip_attack=excluded.skip_attack,
                stamina_restore=excluded.stamina_restore,
                is_available=excluded.is_available
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                max(0, int(template.get("stamina_cost", 0))),
                int(template.get("accuracy_bonus", 0)),
                int(template.get("damage_bonus", 0)),
                int(template.get("evasion_bonus", 0)),
                int(template.get("damage_reduction_bonus", 0)),
                max(0, int(template.get("max_range", 0))),
                1 if template.get("skip_attack", False) else 0,
                max(0, int(template.get("stamina_restore", 0))),
                0 if template.get("available") is False else 1,
            ),
        )


def retire_initial_stance_placeholders(cursor):
    """Remove the first named prototypes after clearing saved references."""
    retired_keys = ("mongoose", "crane")
    cursor.execute(
        """
        DELETE FROM character_stances
        WHERE stance_definition_id IN (
            SELECT id FROM stance_definitions WHERE stance_key IN (?, ?)
        )
        """,
        retired_keys,
    )
    cursor.execute(
        "DELETE FROM stance_definitions WHERE stance_key IN (?, ?)",
        retired_keys,
    )


def engage_npc(cursor, username, x, y, npc_name):
    """Start or retarget a persisted engagement against a hostile NPC in the room."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            "SELECT id FROM players WHERE username=?",
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}
        npcs = cursor.execute(
            """
            SELECT npc_instances.id, npc_templates.name, npc_templates.behavior
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_instances.x=? AND npc_instances.y=?
              AND npc_instances.health > 0
            ORDER BY npc_instances.id
            """,
            (x, y),
        ).fetchall()
        npc = _resolve_named_npc(npcs, npc_name)
        if not npc:
            connection.rollback()
            return {"status": "missing_target"}
        if npc["behavior"] != "hostile":
            connection.rollback()
            return {"status": "not_attackable", "npc_name": npc["name"]}
        pulse_seconds = _pulse_seconds(cursor, player["id"])
        cursor.execute(
            """
            INSERT INTO combat_engagements (player_id, npc_instance_id, next_pulse_at)
            VALUES (?, ?, datetime('now', '+' || ? || ' seconds'))
            ON CONFLICT(player_id) DO UPDATE SET
                npc_instance_id=excluded.npc_instance_id,
                next_pulse_at=excluded.next_pulse_at,
                engaged_at=CURRENT_TIMESTAMP
            """,
            (player["id"], npc["id"], pulse_seconds),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "engaged",
        "npc_name": npc["name"],
        "pulse_seconds": pulse_seconds,
    }


def set_stance(cursor, username, target):
    """Set or clear a character's authored combat stance."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            "SELECT id FROM players WHERE username=?",
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}
        if target.strip().casefold() in {"off", "none", "balanced", "balance", "s3"}:
            cursor.execute("DELETE FROM character_stances WHERE player_id=?", (player["id"],))
            connection.commit()
            return {
                "status": "cleared",
                "name": BALANCED_STANCE_NAME,
                "accuracy_bonus": 0,
                "evasion_bonus": 0,
                "damage_bonus": 0,
                "damage_reduction_bonus": 0,
                "pulse_seconds": BASE_AUTO_ATTACK_SECONDS,
            }
        stances = cursor.execute(
            "SELECT * FROM stance_definitions ORDER BY name"
        ).fetchall()
        stance = _resolve_stance(stances, target)
        if not stance:
            connection.rollback()
            return {"status": "missing"}
        cursor.execute(
            """
            INSERT INTO character_stances (player_id, stance_definition_id)
            VALUES (?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                stance_definition_id=excluded.stance_definition_id
            """,
            (player["id"], stance["id"]),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"status": "set", **dict(stance)}


def list_stances(cursor):
    """Return authored stances in display order."""
    return cursor.execute("SELECT * FROM stance_definitions ORDER BY name").fetchall()


def queue_combat_modifier(
    cursor,
    username,
    action_key,
    accuracy_bonus=0,
    damage_bonus=0,
    max_range=0,
    status_key=None,
    evasion_bonus=0,
    damage_reduction_bonus=0,
    skip_attack=False,
    stamina_restore=0,
):
    """Queue one modifier for the next eligible auto attack."""
    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}
    engagement = cursor.execute(
        "SELECT 1 FROM combat_engagements WHERE player_id=?",
        (player["id"],),
    ).fetchone()
    if not engagement:
        return {"status": "not_engaged"}
    cursor.execute(
        """
        INSERT INTO combat_action_queue (
            player_id, action_key, accuracy_bonus, damage_bonus, max_range, status_key,
            evasion_bonus, damage_reduction_bonus, skip_attack, stamina_restore
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            action_key=excluded.action_key,
            accuracy_bonus=excluded.accuracy_bonus,
            damage_bonus=excluded.damage_bonus,
            max_range=excluded.max_range,
            status_key=excluded.status_key,
            evasion_bonus=excluded.evasion_bonus,
            damage_reduction_bonus=excluded.damage_reduction_bonus,
            skip_attack=excluded.skip_attack,
            stamina_restore=excluded.stamina_restore
        """,
        (
            player["id"],
            action_key,
            int(accuracy_bonus),
            int(damage_bonus),
            max(0, int(max_range)),
            status_key,
            int(evasion_bonus),
            int(damage_reduction_bonus),
            1 if skip_attack else 0,
            max(0, int(stamina_restore)),
        ),
    )
    cursor.connection.commit()
    return {"status": "queued", "action_key": action_key}


def list_combat_techniques(cursor):
    """Return available authored fighting techniques in display order."""
    return cursor.execute(
        """
        SELECT *
        FROM combat_technique_definitions
        WHERE is_available=1
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()


def queue_combat_technique(cursor, username, target):
    """Spend stamina and queue one authored fighting technique for the next pulse."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            "SELECT id, stamina FROM players WHERE username=?",
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}
        engagement = cursor.execute(
            "SELECT 1 FROM combat_engagements WHERE player_id=?",
            (player["id"],),
        ).fetchone()
        if not engagement:
            connection.rollback()
            return {"status": "not_engaged"}
        technique = _resolve_technique(list_combat_techniques(cursor), target)
        if not technique:
            connection.rollback()
            return {"status": "missing"}
        if player["stamina"] < technique["stamina_cost"]:
            connection.rollback()
            return {
                "status": "insufficient_stamina",
                "name": technique["name"],
                "stamina_cost": technique["stamina_cost"],
            }
        cursor.execute(
            "UPDATE players SET stamina=stamina-? WHERE id=?",
            (technique["stamina_cost"], player["id"]),
        )
        cursor.execute(
            """
            INSERT INTO combat_action_queue (
                player_id, action_key, accuracy_bonus, damage_bonus, max_range,
                status_key, evasion_bonus, damage_reduction_bonus,
                skip_attack, stamina_restore
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                action_key=excluded.action_key,
                accuracy_bonus=excluded.accuracy_bonus,
                damage_bonus=excluded.damage_bonus,
                max_range=excluded.max_range,
                status_key=excluded.status_key,
                evasion_bonus=excluded.evasion_bonus,
                damage_reduction_bonus=excluded.damage_reduction_bonus,
                skip_attack=excluded.skip_attack,
                stamina_restore=excluded.stamina_restore
            """,
            (
                player["id"],
                technique["technique_key"],
                technique["accuracy_bonus"],
                technique["damage_bonus"],
                technique["max_range"],
                "technique",
                technique["evasion_bonus"],
                technique["damage_reduction_bonus"],
                technique["skip_attack"],
                technique["stamina_restore"],
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "queued",
        "name": technique["name"],
        "stamina_cost": technique["stamina_cost"],
        "stamina": player["stamina"] - technique["stamina_cost"],
        "skip_attack": bool(technique["skip_attack"]),
    }


def combat_status(cursor, username):
    """Return a character's active stance and optional engagement details."""
    row = cursor.execute(
        """
        SELECT players.id AS player_id, players.x AS player_x, players.y AS player_y,
               stance_definitions.name AS stance_name,
               COALESCE(stance_definitions.accuracy_bonus, 0) AS accuracy_bonus,
               COALESCE(stance_definitions.evasion_bonus, 0) AS evasion_bonus,
               COALESCE(stance_definitions.damage_bonus, 0) AS damage_bonus,
               COALESCE(stance_definitions.damage_reduction_bonus, 0) AS damage_reduction_bonus,
               COALESCE(stance_definitions.pulse_seconds, ?) AS pulse_seconds,
               npc_templates.name AS npc_name, npc_instances.health AS npc_health,
               npc_templates.max_health AS npc_max_health,
               npc_instances.x AS npc_x, npc_instances.y AS npc_y,
               combat_engagements.next_pulse_at,
               combat_action_queue.action_key,
               combat_action_queue.status_key
        FROM players
        LEFT JOIN character_stances ON character_stances.player_id=players.id
        LEFT JOIN stance_definitions ON stance_definitions.id=character_stances.stance_definition_id
        LEFT JOIN combat_engagements ON combat_engagements.player_id=players.id
        LEFT JOIN npc_instances ON npc_instances.id=combat_engagements.npc_instance_id
        LEFT JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
        LEFT JOIN combat_action_queue ON combat_action_queue.player_id=players.id
        WHERE players.username=?
        """,
        (BASE_AUTO_ATTACK_SECONDS, username),
    ).fetchone()
    if not row:
        return None
    status = dict(row)
    status["stance_name"] = status["stance_name"] or BALANCED_STANCE_NAME
    if status["npc_name"]:
        status["distance"] = abs(status["player_x"] - status["npc_x"]) + abs(
            status["player_y"] - status["npc_y"]
        )
        status["auto_in_range"] = status["distance"] <= BASE_AUTO_ATTACK_RANGE
    return status


def clear_engagement(cursor, username):
    """Clear an active engagement and any queued one-shot action."""
    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return False
    cursor.execute("DELETE FROM combat_action_queue WHERE player_id=?", (player["id"],))
    deleted = cursor.execute(
        "DELETE FROM combat_engagements WHERE player_id=?",
        (player["id"],),
    ).rowcount
    cursor.connection.commit()
    return bool(deleted)


def tick_combat(connection, active_usernames=None):
    """Resolve due persisted auto attacks and return player-facing combat events."""
    cursor = connection.cursor()
    active = None if active_usernames is None else set(active_usernames)
    events = []
    try:
        cursor.execute("BEGIN IMMEDIATE")
        rows = cursor.execute(
            """
            SELECT combat_engagements.player_id, combat_engagements.npc_instance_id,
                   players.username, players.x AS player_x, players.y AS player_y,
                   players.health AS player_health, players.max_health,
                   players.strength, players.dexterity, players.agility,
                   npc_instances.x AS npc_x, npc_instances.y AS npc_y,
                   npc_instances.health AS npc_health,
                   npc_templates.name AS npc_name, npc_templates.behavior,
                   npc_templates.attack_damage, npc_templates.accuracy,
                   npc_templates.evasion,
                   COALESCE(stance_definitions.name, ?) AS stance_name,
                   COALESCE(stance_definitions.accuracy_bonus, 0) AS stance_accuracy,
                   COALESCE(stance_definitions.evasion_bonus, 0) AS stance_evasion,
                   COALESCE(stance_definitions.damage_bonus, 0) AS stance_damage,
                   COALESCE(stance_definitions.damage_reduction_bonus, 0) AS stance_damage_reduction,
                   COALESCE(stance_definitions.pulse_seconds, ?) AS pulse_seconds,
                   combat_action_queue.action_key,
                   COALESCE(combat_action_queue.accuracy_bonus, 0) AS queued_accuracy,
                   COALESCE(combat_action_queue.damage_bonus, 0) AS queued_damage,
                   COALESCE(combat_action_queue.max_range, ?) AS queued_range,
                   COALESCE(combat_action_queue.evasion_bonus, 0) AS queued_evasion,
                   COALESCE(combat_action_queue.damage_reduction_bonus, 0) AS queued_damage_reduction,
                   COALESCE(combat_action_queue.skip_attack, 0) AS queued_skip_attack,
                   COALESCE(combat_action_queue.stamina_restore, 0) AS queued_stamina_restore
            FROM combat_engagements
            JOIN players ON players.id=combat_engagements.player_id
            JOIN npc_instances ON npc_instances.id=combat_engagements.npc_instance_id
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            LEFT JOIN character_stances ON character_stances.player_id=players.id
            LEFT JOIN stance_definitions ON stance_definitions.id=character_stances.stance_definition_id
            LEFT JOIN combat_action_queue ON combat_action_queue.player_id=players.id
            WHERE combat_engagements.next_pulse_at <= CURRENT_TIMESTAMP
            ORDER BY combat_engagements.player_id
            """,
            (BALANCED_STANCE_NAME, BASE_AUTO_ATTACK_SECONDS, BASE_AUTO_ATTACK_RANGE),
        ).fetchall()
        for row in rows:
            if active is not None and row["username"] not in active:
                _delete_engagement(cursor, row["player_id"])
                continue
            event = _resolve_pulse(cursor, row)
            events.append(event)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return events


def _resolve_pulse(cursor, row):
    npc = cursor.execute(
        "SELECT x, y, health FROM npc_instances WHERE id=?",
        (row["npc_instance_id"],),
    ).fetchone()
    if not npc:
        _delete_engagement(cursor, row["player_id"])
        return {
            "username": row["username"],
            "npc_name": row["npc_name"],
            "stance_name": row["stance_name"],
            "distance": 0,
            "player_x": row["player_x"],
            "player_y": row["player_y"],
            "action_key": row["action_key"],
            "status": "ended",
        }
    distance = abs(row["player_x"] - npc["x"]) + abs(row["player_y"] - npc["y"])
    event = {
        "username": row["username"],
        "npc_name": row["npc_name"],
        "stance_name": row["stance_name"],
        "distance": distance,
        "player_x": row["player_x"],
        "player_y": row["player_y"],
        "action_key": row["action_key"],
    }
    if npc["health"] <= 0:
        _delete_engagement(cursor, row["player_id"])
        return {**event, "status": "ended"}

    attack_range = max(BASE_AUTO_ATTACK_RANGE, row["queued_range"])
    cursor.execute(
        """
        UPDATE combat_engagements
        SET next_pulse_at=datetime('now', '+' || ? || ' seconds')
        WHERE player_id=?
        """,
        (row["pulse_seconds"], row["player_id"]),
    )
    if distance > attack_range:
        return {**event, "status": "out_of_range", "attack_range": attack_range}

    add_fatigue(cursor, row["username"], 1)
    skip_attack = bool(row["queued_skip_attack"])
    player_damage = 0 if skip_attack else max(
        1,
        row["strength"] // 2
        + _equipped_damage_bonus(cursor, row["player_id"])
        + row["stance_damage"]
        + row["queued_damage"],
    )
    player_hit = False if skip_attack else random.randint(1, 100) <= hit_chance(
        row["dexterity"] + row["stance_accuracy"] + row["queued_accuracy"],
        row["evasion"],
    )
    npc_health = npc["health"]
    if player_hit:
        npc_health = max(0, npc_health - player_damage)
        cursor.execute(
            "UPDATE npc_instances SET health=? WHERE id=?",
            (npc_health, row["npc_instance_id"]),
        )
    stamina_restored = 0
    if row["queued_stamina_restore"]:
        stamina = cursor.execute(
            "SELECT stamina, max_stamina FROM players WHERE id=?",
            (row["player_id"],),
        ).fetchone()
        updated_stamina = min(
            stamina["max_stamina"],
            stamina["stamina"] + row["queued_stamina_restore"],
        )
        stamina_restored = updated_stamina - stamina["stamina"]
        cursor.execute(
            "UPDATE players SET stamina=? WHERE id=?",
            (updated_stamina, row["player_id"]),
        )
    cursor.execute("DELETE FROM combat_action_queue WHERE player_id=?", (row["player_id"],))
    if npc_health == 0:
        cursor.execute(
            "UPDATE npc_instances SET defeated_at=CURRENT_TIMESTAMP WHERE id=?",
            (row["npc_instance_id"],),
        )
        _delete_engagement(cursor, row["player_id"])
        return {
            **event,
            "status": "npc_defeated",
            "player_hit": player_hit,
            "player_damage": player_damage,
            "skip_attack": skip_attack,
            "stamina_restored": stamina_restored,
        }

    npc_hit = False
    substitution = None
    player_health = row["player_health"]
    player_defeated = False
    if distance <= BASE_AUTO_ATTACK_RANGE:
        npc_hit = random.randint(1, 100) <= hit_chance(
            row["accuracy"],
            row["agility"] + row["stance_evasion"] + row["queued_evasion"],
        )
        substitution = consume_substitution(cursor, row["username"]) if npc_hit else None
        if npc_hit and not substitution:
            npc_damage = max(
                0,
                row["attack_damage"]
                - row["stance_damage_reduction"]
                - row["queued_damage_reduction"],
            )
            player_health = max(0, player_health - npc_damage)
            player_defeated = player_health == 0
            if player_defeated:
                player_health = row["max_health"]
                _delete_engagement(cursor, row["player_id"])
            cursor.execute(
                "UPDATE players SET health=? WHERE id=?",
                (player_health, row["player_id"]),
            )
    return {
        **event,
        "status": "exchange",
        "player_hit": player_hit,
        "player_damage": player_damage,
        "npc_health": npc_health,
        "npc_hit": npc_hit,
        "npc_damage": max(
            0,
            row["attack_damage"]
            - row["stance_damage_reduction"]
            - row["queued_damage_reduction"],
        ),
        "player_health": player_health,
        "player_defeated": player_defeated,
        "substitution": substitution,
        "skip_attack": skip_attack,
        "stamina_restored": stamina_restored,
    }


def _pulse_seconds(cursor, player_id):
    row = cursor.execute(
        """
        SELECT stance_definitions.pulse_seconds
        FROM character_stances
        JOIN stance_definitions ON stance_definitions.id=character_stances.stance_definition_id
        WHERE character_stances.player_id=?
        """,
        (player_id,),
    ).fetchone()
    return row["pulse_seconds"] if row else BASE_AUTO_ATTACK_SECONDS


def _resolve_stance(stances, target):
    query = target.strip().casefold()
    exact = [
        stance
        for stance in stances
        if stance["name"].casefold() == query or stance["stance_key"].casefold() == query
    ]
    matches = exact or [
        stance
        for stance in stances
        if stance["name"].casefold().startswith(query)
        or stance["stance_key"].casefold().startswith(query)
    ]
    return matches[0] if len(matches) == 1 else None


def _resolve_technique(techniques, target):
    query = target.strip().casefold()
    exact = [
        technique
        for technique in techniques
        if technique["name"].casefold() == query
        or technique["technique_key"].casefold() == query
    ]
    matches = exact or [
        technique
        for technique in techniques
        if technique["name"].casefold().startswith(query)
        or technique["technique_key"].casefold().startswith(query)
    ]
    return matches[0] if len(matches) == 1 else None


def _delete_engagement(cursor, player_id):
    cursor.execute("DELETE FROM combat_action_queue WHERE player_id=?", (player_id,))
    cursor.execute("DELETE FROM combat_engagements WHERE player_id=?", (player_id,))
