"""Import authored JSON content into persistent live database state."""

import json
import os

from combat import create_combat_tables, sync_combat_technique_templates, sync_stance_templates
from items import create_item_tables
from npcs import create_npc_tables
from techniques import create_technique_tables, sync_jutsu_templates, sync_skill_templates


def _words(value, default=None):
    if value is None:
        return default or []
    if isinstance(value, str):
        return value.split()
    return list(value)


def create_authored_content_tables(cursor):
    """Track one-time authored spawns independently of mutable instances."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS authored_content_seeds (
            seed_key TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def sync_authored_content(connection, zones_directory, overlays):
    """Import templates and create missing authored live instances once."""
    cursor = connection.cursor()
    create_item_tables(cursor)
    create_npc_tables(cursor)
    create_authored_content_tables(cursor)
    create_technique_tables(cursor)
    create_combat_tables(cursor)
    coordinates_by_vnum = {
        overlay["vnum"]: coordinates
        for coordinates, overlay in overlays.items()
    }
    created = {"item_spawns": 0, "npc_spawns": 0}

    for zone_file in sorted(os.listdir(zones_directory)):
        if not zone_file.endswith(".json"):
            continue
        with open(os.path.join(zones_directory, zone_file), "r", encoding="utf-8") as file:
            zone_data = json.load(file)
        content_key = zone_data.get("content_key", os.path.splitext(zone_file)[0])
        _sync_item_templates(cursor, zone_data.get("item_templates", []))
        _sync_npc_templates(cursor, zone_data.get("npc_templates", []))
        sync_skill_templates(cursor, zone_data.get("skill_templates", []))
        sync_jutsu_templates(cursor, zone_data.get("jutsu_templates", []))
        sync_stance_templates(cursor, zone_data.get("stance_templates", []))
        sync_combat_technique_templates(cursor, zone_data.get("combat_technique_templates", []))
        created["item_spawns"] += _sync_item_spawns(
            cursor,
            content_key,
            zone_data.get("item_spawns", []),
            coordinates_by_vnum,
        )
        created["npc_spawns"] += _sync_npc_spawns(
            cursor,
            content_key,
            zone_data.get("npc_spawns", []),
            coordinates_by_vnum,
        )

    connection.commit()
    return created


def _sync_item_templates(cursor, templates):
    for template in templates:
        cursor.execute(
            """
            INSERT INTO item_definitions (
                item_key, name, description, keywords, item_type,
                equipment_slot, use_text, damage_bonus,
                throw_damage, nutrition_restore, hydration_restore,
                value, weight, stack_limit, container_capacity, flags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                keywords=excluded.keywords,
                item_type=excluded.item_type,
                equipment_slot=excluded.equipment_slot,
                use_text=excluded.use_text,
                damage_bonus=excluded.damage_bonus,
                throw_damage=excluded.throw_damage,
                nutrition_restore=excluded.nutrition_restore,
                hydration_restore=excluded.hydration_restore,
                value=excluded.value,
                weight=excluded.weight,
                stack_limit=excluded.stack_limit,
                container_capacity=excluded.container_capacity,
                flags=excluded.flags
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                " ".join(_words(template.get("keywords", []))),
                template.get("item_type", "misc"),
                template.get("equipment_slot"),
                template.get("use_text", ""),
                int(template.get("damage_bonus", 0)),
                int(template.get("throw_damage", 0)),
                int(template.get("nutrition_restore", 0)),
                int(template.get("hydration_restore", 0)),
                int(template.get("value", 0)),
                int(template.get("weight", 0)),
                int(template.get("stack_limit", 1)),
                int(template.get("container_capacity", 0)),
                " ".join(_words(template.get("flags"), ["takeable"])),
            ),
        )


def _sync_npc_templates(cursor, templates):
    for template in templates:
        cursor.execute(
            """
            INSERT INTO npc_templates (
                npc_key, name, description, dialogue, behavior,
                max_health, attack_damage, accuracy, evasion, respawn_seconds,
                loot_table, room_emote, movement_policy, leash_radius, aggression_policy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(npc_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                dialogue=excluded.dialogue,
                behavior=excluded.behavior,
                max_health=excluded.max_health,
                attack_damage=excluded.attack_damage,
                accuracy=excluded.accuracy,
                evasion=excluded.evasion,
                respawn_seconds=excluded.respawn_seconds,
                loot_table=excluded.loot_table,
                room_emote=excluded.room_emote,
                movement_policy=excluded.movement_policy,
                leash_radius=excluded.leash_radius,
                aggression_policy=excluded.aggression_policy
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                template["dialogue"],
                template.get("behavior", "static"),
                int(template.get("max_health", 1)),
                int(template.get("attack_damage", 0)),
                int(template.get("accuracy", 5)),
                int(template.get("evasion", 5)),
                int(template.get("respawn_seconds", 60)),
                " ".join(_words(template.get("loot_table", []))),
                template.get("room_emote", ""),
                template.get("movement_policy", "static"),
                int(template.get("leash_radius", 0)),
                template.get("aggression_policy", "passive"),
            ),
        )


def _sync_item_spawns(cursor, content_key, spawns, coordinates_by_vnum):
    created = 0
    for spawn in spawns:
        seed_key = f"{content_key}:{spawn['key']}"
        if _seed_exists(cursor, seed_key):
            continue
        existing = cursor.execute(
            "SELECT 1 FROM room_items WHERE seed_key=?",
            (seed_key,),
        ).fetchone()
        if not existing:
            x, y = _spawn_coordinates(spawn, coordinates_by_vnum)
            item_definition_id = cursor.execute(
                "SELECT id FROM item_definitions WHERE item_key=?",
                (spawn["item"],),
            ).fetchone()[0]
            cursor.execute(
                """
                INSERT INTO room_items (item_definition_id, x, y, seed_key)
                VALUES (?, ?, ?, ?)
                """,
                (item_definition_id, x, y, seed_key),
            )
            created += 1
        _record_seed(cursor, seed_key, "item")
    return created


def _sync_npc_spawns(cursor, content_key, spawns, coordinates_by_vnum):
    created = 0
    for spawn in spawns:
        seed_key = f"{content_key}:npc:{spawn['key']}"
        existing = cursor.execute(
            "SELECT 1 FROM npc_instances WHERE seed_key=?",
            (seed_key,),
        ).fetchone()
        if existing:
            continue
        x, y = _spawn_coordinates(spawn, coordinates_by_vnum)
        npc_template = cursor.execute(
            "SELECT id, max_health FROM npc_templates WHERE npc_key=?",
            (spawn["npc"],),
        ).fetchone()
        cursor.execute(
            """
            INSERT INTO npc_instances (
                npc_template_id, x, y, home_x, home_y, seed_key, health
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (npc_template["id"], x, y, x, y, seed_key, npc_template["max_health"]),
        )
        _record_seed(cursor, seed_key, "npc")
        created += 1
    return created


def _spawn_coordinates(spawn, coordinates_by_vnum):
    vnum = int(spawn["vnum"])
    if vnum not in coordinates_by_vnum:
        raise ValueError(f"Authored spawn references unavailable VNUM {vnum}.")
    return coordinates_by_vnum[vnum]


def _seed_exists(cursor, seed_key):
    return bool(
        cursor.execute(
            "SELECT 1 FROM authored_content_seeds WHERE seed_key=?",
            (seed_key,),
        ).fetchone()
    )


def _record_seed(cursor, seed_key, content_type):
    cursor.execute(
        """
        INSERT OR IGNORE INTO authored_content_seeds (seed_key, content_type)
        VALUES (?, ?)
        """,
        (seed_key, content_type),
    )
