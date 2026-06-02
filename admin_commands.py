import json
import os
import logging
import re
from copy import deepcopy
from command_system import CommandSpec
from content import sync_authored_content
from locations import DIRECTION_OFFSETS, is_within_bounds, online_players, teleport_player
from twisted.internet import reactor
from shinobi_mud import ACTIVE_CONFIG, UTILITIES, WORLD_MAP, WORLD_OVERLAYS, players_in_rooms

logging.info("admin_commands imported")


def zone_directory():
    """Return the configured directory for authored zone JSON files."""
    return ACTIVE_CONFIG.get("zone_directory", "zones")


def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """
    Creates a new zone with a specified range of VNUMs.
    """
    try:
        if not zone_name.strip():
            protocol.sendLine(b"Zone name cannot be empty.")
            return

        start_vnum, end_vnum = int(start_vnum), int(end_vnum)

        authored_zone_directory = zone_directory()
        os.makedirs(authored_zone_directory, exist_ok=True)
        zone_file_path = os.path.join(authored_zone_directory, f"{zone_name}.json")
        logging.info(f"Creating zone file at: {zone_file_path}")

        if os.path.exists(zone_file_path):
            protocol.sendLine(b"Zone already exists.")
            return

        zone_data = {
            "name": zone_name,
            "range": {"start": start_vnum, "end": end_vnum},
            "rooms": {}
        }

        with open(zone_file_path, "w") as zone_file:
            json.dump(zone_data, zone_file, indent=4)

        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum}.".encode('utf-8'))
        logging.info(f"Zone {zone_name} created with range {start_vnum}-{end_vnum}.")

    except ValueError:
        protocol.sendLine(b"VNUMs must be integers.")
    except Exception as e:
        logging.error(f"Error creating zone: {e}", exc_info=True)
        protocol.sendLine(f"Failed to create zone: {e}".encode('utf-8'))

def goto_vnum(protocol, vnum):
    """Teleport an admin to an authored room without replacing grid coordinates."""
    located_overlay = UTILITIES["find_overlay_by_vnum"](WORLD_OVERLAYS, vnum)
    if not located_overlay:
        protocol.sendLine(f"No overlay room found for VNUM {vnum}.".encode("utf-8"))
        return

    coordinates, overlay = located_overlay
    if not teleport_player(protocol, *coordinates, WORLD_MAP, players_in_rooms):
        protocol.sendLine(b"Overlay destination falls outside the world map.")
        return

    protocol.sendLine(
        f"Teleported to {overlay['zone_name']} [{overlay['vnum']}] at {coordinates}.".encode("utf-8")
    )
    protocol.display_room()


def goto_grid(protocol, x, y):
    """Teleport an admin to canonical grid coordinates."""
    coordinates = int(x), int(y)
    if not teleport_player(protocol, *coordinates, WORLD_MAP, players_in_rooms):
        protocol.sendLine(b"Grid destination falls outside the world map.")
        return

    protocol.sendLine(f"Teleported to grid location {coordinates}.".encode("utf-8"))
    protocol.display_room()


def goto_player(protocol, username):
    """Teleport an admin to another online character."""
    target = next(
        (
            player
            for player in online_players(players_in_rooms)
            if player.username.lower() == username.lower()
        ),
        None,
    )
    if not target:
        protocol.sendLine(f"Online player not found: {username}".encode("utf-8"))
        return

    if not teleport_player(protocol, target.x, target.y, WORLD_MAP, players_in_rooms):
        protocol.sendLine(b"Player destination falls outside the world map.")
        return

    protocol.sendLine(
        f"Teleported to {target.username} at ({target.x}, {target.y}).".encode("utf-8")
    )
    protocol.display_room()


def goto(protocol, *args):
    """Dispatch backward-compatible VNUM, grid, and player teleports."""
    if len(args) == 1 and args[0].isdigit():
        goto_vnum(protocol, args[0])
    elif len(args) == 3 and args[0].lower() == "grid":
        goto_grid(protocol, args[1], args[2])
    elif len(args) == 2 and args[0].lower() == "player":
        goto_player(protocol, args[1])
    else:
        protocol.sendLine(b"Usage: goto <vnum> | goto grid <x> <y> | goto player <name>")


def zoneinfo(protocol, vnum=None):
    """Inspect the overlay at the current location or a requested VNUM."""
    if vnum is None:
        coordinates = (protocol.x, protocol.y)
        overlay = WORLD_OVERLAYS.get(coordinates)
    else:
        located_overlay = UTILITIES["find_overlay_by_vnum"](WORLD_OVERLAYS, vnum)
        if not located_overlay:
            protocol.sendLine(f"No overlay room found for VNUM {vnum}.".encode("utf-8"))
            return
        coordinates, overlay = located_overlay

    if not overlay:
        protocol.sendLine(b"No authored overlay exists at your current location.")
        return

    room = overlay["room"]
    protocol.sendLine(
        f"{overlay['zone_name']} [{overlay['vnum']}] at {coordinates}".encode("utf-8")
    )
    protocol.sendLine(f"Room title: {room.get('name', 'Unnamed Room')}".encode("utf-8"))
    protocol.sendLine(room.get("description", "No description.").encode("utf-8"))


def placezone(protocol, zone_file, anchor_x, anchor_y):
    """Persist a zone anchor and reload the live coordinate overlay registry."""
    safe_name = os.path.basename(zone_file)
    if not safe_name.endswith(".json"):
        safe_name += ".json"
    zone_path = os.path.join(zone_directory(), safe_name)
    if not os.path.isfile(zone_path):
        protocol.sendLine(f"Zone file not found: {safe_name}".encode("utf-8"))
        return

    try:
        with open(zone_path, "r") as file:
            zone_data = json.load(file)
        original_zone_data = dict(zone_data)
        zone_data["anchor"] = {"x": int(anchor_x), "y": int(anchor_y)}
        with open(zone_path, "w") as file:
            json.dump(zone_data, file, indent=4)
            file.write("\n")
        UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS, zone_directory())
        if any(
            not is_within_bounds(WORLD_MAP, *coordinates)
            for coordinates in WORLD_OVERLAYS
        ):
            raise ValueError("Zone placement falls outside the world map.")
    except (ValueError, KeyError) as exc:
        if "original_zone_data" in locals():
            with open(zone_path, "w") as file:
                json.dump(original_zone_data, file, indent=4)
                file.write("\n")
            UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS, zone_directory())
        protocol.sendLine(f"Unable to place zone: {exc}".encode("utf-8"))
        return

    protocol.sendLine(
        f"Placed {zone_data['name']} at ({anchor_x}, {anchor_y}) with {len(zone_data['rooms'])} overlay rooms.".encode("utf-8")
    )


def reloadcontent(protocol):
    """Reload zone JSON overlays, templates, and missing authored spawns."""
    try:
        UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS, zone_directory())
        imported = sync_authored_content(
            protocol.cursor.connection,
            zone_directory(),
            WORLD_OVERLAYS,
        )
        protocol.sendLine(
            (
                "Authored content reloaded. "
                f"Created {imported['item_spawns']} item spawns and "
                f"{imported['npc_spawns']} NPC spawns."
            ).encode("utf-8")
        )
    except Exception as exc:
        logging.error("Unable to reload authored content: %s", exc, exc_info=True)
        protocol.sendLine(b"Unable to reload authored content.")


def _write_zone(zone_path, zone_data):
    """Persist formatted authored zone JSON."""
    with open(zone_path, "w", encoding="utf-8") as file:
        json.dump(zone_data, file, indent=4)
        file.write("\n")


def _load_zone_for_vnum(vnum):
    """Return the authored zone file and data containing an existing room."""
    target = str(vnum)
    for file_name in sorted(os.listdir(zone_directory())):
        if not file_name.endswith(".json"):
            continue
        zone_path = os.path.join(zone_directory(), file_name)
        with open(zone_path, "r", encoding="utf-8") as file:
            zone_data = json.load(file)
        if target in zone_data.get("rooms", {}):
            return zone_path, zone_data
    return None, None


def _reload_valid_overlays():
    """Reload overlays and reject edits that leave the world map."""
    UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS, zone_directory())
    if any(not is_within_bounds(WORLD_MAP, *coordinates) for coordinates in WORLD_OVERLAYS):
        raise ValueError("Authored room falls outside the world map.")


def _current_authored_room(protocol):
    """Return the current overlay, zone file, and zone data for an admin."""
    overlay = WORLD_OVERLAYS.get((protocol.x, protocol.y))
    if not overlay:
        raise ValueError("Stand in an authored overlay room first.")
    zone_path, zone_data = _load_zone_for_vnum(overlay["vnum"])
    if not zone_data:
        raise ValueError(f"Unable to locate zone JSON for VNUM {overlay['vnum']}.")
    return overlay, zone_path, zone_data


def _find_zone_file(zone_file):
    """Return a safe authored zone path from a builder-facing file key."""
    safe_name = os.path.basename(zone_file)
    if not safe_name.endswith(".json"):
        safe_name += ".json"
    return os.path.join(zone_directory(), safe_name)


def _all_authored_zones():
    """Yield authored zone paths and parsed JSON in stable file order."""
    for file_name in sorted(os.listdir(zone_directory())):
        if not file_name.endswith(".json"):
            continue
        zone_path = os.path.join(zone_directory(), file_name)
        with open(zone_path, "r", encoding="utf-8") as file:
            yield zone_path, json.load(file)


def _find_template(template_type, template_key):
    """Return the zone file, zone data, and one globally keyed template."""
    collection = f"{template_type}_templates"
    for zone_path, zone_data in _all_authored_zones():
        for template in zone_data.get(collection, []):
            if template["key"] == template_key:
                return zone_path, zone_data, template
    return None, None, None


def _validate_builder_key(key, label):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
        raise ValueError(f"{label} key must use lowercase letters, numbers, and single hyphens.")


def _required_text(value, label):
    """Return trimmed builder prose while rejecting accidental blank fields."""
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value


def _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data, reload_overlays=False):
    """Persist a zone mutation and restore JSON plus overlays if validation fails."""
    _write_zone(zone_path, zone_data)
    try:
        if reload_overlays:
            _reload_valid_overlays()
        sync_authored_content(protocol.cursor.connection, zone_directory(), WORLD_OVERLAYS)
    except Exception:
        protocol.cursor.connection.rollback()
        _write_zone(zone_path, original_zone_data)
        if reload_overlays:
            _reload_valid_overlays()
        raise


def buildzone(protocol, zone_key, start_vnum, end_vnum, anchor_x, anchor_y, room_title):
    """Create an anchored zone with one usable starting room and teleport there."""
    try:
        _validate_builder_key(zone_key, "Zone")
        room_title = _required_text(room_title, "Room title")
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        anchor_x, anchor_y = int(anchor_x), int(anchor_y)
        if start_vnum > end_vnum:
            raise ValueError("Zone VNUM start must not exceed its end.")
        if not is_within_bounds(WORLD_MAP, anchor_x, anchor_y):
            raise ValueError("Zone anchor falls outside the world map.")
        if (anchor_x, anchor_y) in WORLD_OVERLAYS:
            raise ValueError(f"An authored room already exists at ({anchor_x}, {anchor_y}).")
        for _, authored_zone in _all_authored_zones():
            authored_range = authored_zone["range"]
            if start_vnum <= int(authored_range["end"]) and end_vnum >= int(authored_range["start"]):
                raise ValueError(f"VNUM range overlaps authored zone {authored_zone['name']}.")

        zone_path = _find_zone_file(zone_key)
        if os.path.exists(zone_path):
            raise ValueError(f"Zone already exists: {zone_key}")
        zone_data = {
            "name": room_title,
            "content_key": zone_key,
            "range": {"start": start_vnum, "end": end_vnum},
            "anchor": {"x": anchor_x, "y": anchor_y},
            "rooms": {
                str(start_vnum): {
                    "name": room_title,
                    "description": "An unfinished authored room.",
                    "flags": [],
                    "exits": {},
                    "x_offset": 0,
                    "y_offset": 0,
                }
            },
            "item_templates": [],
            "item_spawns": [],
            "npc_templates": [],
            "npc_spawns": [],
        }
        _write_zone(zone_path, zone_data)
        try:
            _reload_valid_overlays()
        except Exception:
            os.remove(zone_path)
            _reload_valid_overlays()
            raise
        if not teleport_player(protocol, anchor_x, anchor_y, WORLD_MAP, players_in_rooms):
            raise ValueError("Unable to teleport to the new zone anchor.")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to build zone: {exc}".encode("utf-8"))
        return

    protocol.sendLine(
        f"Built {room_title} [{start_vnum}] at ({anchor_x}, {anchor_y}) and moved there.".encode("utf-8")
    )
    protocol.display_room()


def zonelist(protocol):
    """List authored zones with ranges, anchors, and room counts."""
    try:
        zones = list(_all_authored_zones())
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to list zones: {exc}".encode("utf-8"))
        return
    protocol.sendLine(b"Authored Zones")
    for zone_path, zone_data in zones:
        anchor = zone_data.get("anchor")
        anchor_text = f"({anchor['x']}, {anchor['y']})" if anchor else "unplaced"
        authored_range = zone_data["range"]
        protocol.sendLine(
            (
                f"  {os.path.basename(zone_path)}: {zone_data['name']} "
                f"[{authored_range['start']}-{authored_range['end']}] "
                f"anchor={anchor_text} rooms={len(zone_data.get('rooms', {}))}"
            ).encode("utf-8")
        )


def rstat(protocol, vnum=None):
    """Inspect an authored room's builder-facing fields."""
    try:
        if vnum is None:
            overlay, _, zone_data = _current_authored_room(protocol)
        else:
            located_overlay = UTILITIES["find_overlay_by_vnum"](WORLD_OVERLAYS, vnum)
            if not located_overlay:
                raise ValueError(f"No overlay room found for VNUM {vnum}.")
            _, overlay = located_overlay
            _, zone_data = _load_zone_for_vnum(overlay["vnum"])
        room = zone_data["rooms"][str(overlay["vnum"])]
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to inspect room: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Room [{overlay['vnum']}] {room.get('name', 'Unnamed Room')}".encode("utf-8"))
    protocol.sendLine(f"  Zone: {zone_data['name']}".encode("utf-8"))
    protocol.sendLine(f"  Description: {room.get('description', 'No description.')}".encode("utf-8"))
    protocol.sendLine(f"  Offsets: ({room.get('x_offset', 0)}, {room.get('y_offset', 0)})".encode("utf-8"))
    protocol.sendLine(f"  Flags: {', '.join(room.get('flags', [])) or 'None'}".encode("utf-8"))
    exits = ", ".join(f"{direction}={target}" for direction, target in room.get("exits", {}).items())
    protocol.sendLine(f"  Exits: {exits or 'None'}".encode("utf-8"))


def redit(protocol, field, value):
    """Edit common authored-room fields while preserving overlay validity."""
    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        room = zone_data["rooms"][str(overlay["vnum"])]
        original_zone_data = deepcopy(zone_data)
        field = field.lower()
        if field == "title":
            room["name"] = _required_text(value, "Room title")
        elif field in {"desc", "description"}:
            room["description"] = _required_text(value, "Room description")
        elif field == "flag":
            parts = value.lower().split()
            if len(parts) != 2 or parts[1] not in {"on", "off"}:
                raise ValueError("Usage: redit flag <flag> <on|off>")
            flags = set(room.get("flags", []))
            if parts[1] == "on":
                flags.add(parts[0])
            else:
                flags.discard(parts[0])
            room["flags"] = sorted(flags)
        elif field == "exit":
            parts = value.lower().split()
            if len(parts) != 2 or parts[0] not in DIRECTION_OFFSETS:
                raise ValueError("Usage: redit exit <direction> <vnum|none>")
            if parts[1] == "none":
                room.setdefault("exits", {}).pop(parts[0], None)
            elif parts[1].isdigit() and _load_zone_for_vnum(parts[1])[1]:
                room.setdefault("exits", {})[parts[0]] = int(parts[1])
            else:
                raise ValueError("Exit target must be an existing authored VNUM or none.")
        else:
            raise ValueError("Room field must be title, desc, flag, or exit.")
        _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data, reload_overlays=True)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to edit room: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Updated room [{overlay['vnum']}] {field}.".encode("utf-8"))


def dig(protocol, direction, room_name):
    """Create a coordinate-aware authored overlay room and reciprocal exit."""
    direction = direction.lower()
    if direction not in DIRECTION_OFFSETS:
        protocol.sendLine(b"Direction must be north, south, east, or west.")
        return

    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        room = zone_data["rooms"][str(overlay["vnum"])]
        room_name = _required_text(room_name, "Room title")
        if direction in room.get("exits", {}):
            raise ValueError(f"An authored {direction} exit already exists.")

        dx, dy = DIRECTION_OFFSETS[direction]
        coordinates = protocol.x + dx, protocol.y + dy
        if coordinates in WORLD_OVERLAYS:
            raise ValueError(f"An authored room already exists at {coordinates}.")
        if not is_within_bounds(WORLD_MAP, *coordinates):
            raise ValueError("The new room would fall outside the world map.")

        new_vnum = next_free_vnum(zone_data)
        if new_vnum is None:
            raise ValueError("The zone has no free VNUMs.")

        original_zone_data = deepcopy(zone_data)
        room.setdefault("exits", {})[direction] = new_vnum
        zone_data["rooms"][str(new_vnum)] = {
            "name": room_name,
            "description": "An unfinished authored room.",
            "flags": [],
            "exits": {reverse_dir(direction): overlay["vnum"]},
            "x_offset": int(room.get("x_offset", 0)) + dx,
            "y_offset": int(room.get("y_offset", 0)) + dy,
        }
        _write_zone(zone_path, zone_data)
        try:
            _reload_valid_overlays()
        except Exception:
            _write_zone(zone_path, original_zone_data)
            _reload_valid_overlays()
            raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to dig room: {exc}".encode("utf-8"))
        return

    protocol.sendLine(
        f"Dug {direction} to {room_name} [{new_vnum}] at {coordinates}.".encode("utf-8")
    )


def roomdesc(protocol, description):
    """Replace the current authored overlay room description."""
    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        original_zone_data = deepcopy(zone_data)
        zone_data["rooms"][str(overlay["vnum"])]["description"] = _required_text(
            description,
            "Room description",
        )
        _write_zone(zone_path, zone_data)
        try:
            _reload_valid_overlays()
        except Exception:
            _write_zone(zone_path, original_zone_data)
            _reload_valid_overlays()
            raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to update room description: {exc}".encode("utf-8"))
        return

    protocol.sendLine(f"Updated room description for [{overlay['vnum']}].".encode("utf-8"))


def _authored_npc_template_keys():
    """Return NPC template keys currently declared in zone JSON."""
    keys = set()
    for file_name in sorted(os.listdir(zone_directory())):
        if not file_name.endswith(".json"):
            continue
        with open(os.path.join(zone_directory(), file_name), "r", encoding="utf-8") as file:
            authored_zone = json.load(file)
        keys.update(template["key"] for template in authored_zone.get("npc_templates", []))
    return keys


def mstat(protocol, npc_key):
    """Inspect one globally keyed authored NPC template."""
    try:
        _, zone_data, template = _find_template("npc", npc_key)
        if not template:
            raise ValueError(f"Unknown authored NPC template: {npc_key}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to inspect NPC template: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"NPC {template['key']}: {template['name']}".encode("utf-8"))
    protocol.sendLine(f"  Zone: {zone_data['name']}".encode("utf-8"))
    protocol.sendLine(f"  Description: {template['description']}".encode("utf-8"))
    protocol.sendLine(f"  Dialogue: {template['dialogue']}".encode("utf-8"))
    protocol.sendLine(f"  Behavior: {template.get('behavior', 'static')}".encode("utf-8"))
    protocol.sendLine(
        (
            f"  Combat: health={template.get('max_health', 1)} damage={template.get('attack_damage', 0)} "
            f"accuracy={template.get('accuracy', 5)} evasion={template.get('evasion', 5)} "
            f"respawn={template.get('respawn_seconds', 60)}s"
        ).encode("utf-8")
    )


def medit(protocol, npc_key, field, value):
    """Edit one authored NPC template and synchronize live definition metadata."""
    integer_fields = {
        "health": "max_health",
        "maxhealth": "max_health",
        "damage": "attack_damage",
        "accuracy": "accuracy",
        "evasion": "evasion",
        "respawn": "respawn_seconds",
    }
    try:
        zone_path, zone_data, template = _find_template("npc", npc_key)
        if not template:
            raise ValueError(f"Unknown authored NPC template: {npc_key}")
        original_zone_data = deepcopy(zone_data)
        field = field.lower()
        if field == "name":
            template["name"] = _required_text(value, "NPC name")
        elif field in {"desc", "description"}:
            template["description"] = _required_text(value, "NPC description")
        elif field == "dialogue":
            template["dialogue"] = _required_text(value, "NPC dialogue")
        elif field == "behavior":
            if value.lower() not in {"static", "hostile"}:
                raise ValueError("NPC behavior must be static or hostile.")
            template["behavior"] = value.lower()
        elif field in integer_fields:
            numeric_value = int(value)
            if numeric_value < 0:
                raise ValueError("NPC numeric fields cannot be negative.")
            template[integer_fields[field]] = numeric_value
        else:
            raise ValueError("NPC field must be name, desc, dialogue, behavior, health, damage, accuracy, evasion, or respawn.")
        _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to edit NPC template: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Updated authored NPC {npc_key} {field}.".encode("utf-8"))


def createnpc(protocol, npc_key, npc_name):
    """Persist and import a basic static authored NPC template."""
    try:
        _, zone_path, zone_data = _current_authored_room(protocol)
        _validate_builder_key(npc_key, "NPC")
        npc_name = _required_text(npc_name, "NPC name")
        if npc_key in _authored_npc_template_keys():
            raise ValueError(f"Authored NPC template already exists: {npc_key}")

        original_zone_data = deepcopy(zone_data)
        zone_data.setdefault("npc_templates", []).append(
            {
                "key": npc_key,
                "name": npc_name,
                "description": f"{npc_name} waits here.",
                "dialogue": f"{npc_name} has nothing to say yet.",
                "behavior": "static",
            }
        )
        _write_zone(zone_path, zone_data)
        try:
            sync_authored_content(
                protocol.cursor.connection,
                zone_directory(),
                WORLD_OVERLAYS,
            )
        except Exception:
            protocol.cursor.connection.rollback()
            _write_zone(zone_path, original_zone_data)
            raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to create NPC template: {exc}".encode("utf-8"))
        return

    protocol.sendLine(f"Created authored NPC template {npc_key}: {npc_name}.".encode("utf-8"))


def spawnnpc(protocol, npc_key):
    """Persist and import a spawn for an existing authored NPC template."""
    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        if npc_key not in _authored_npc_template_keys():
            raise ValueError(f"Unknown authored NPC template: {npc_key}")

        original_zone_data = deepcopy(zone_data)
        existing_keys = {spawn["key"] for spawn in zone_data.get("npc_spawns", [])}
        base_key = f"builder-{npc_key}-{overlay['vnum']}"
        spawn_key = base_key
        suffix = 2
        while spawn_key in existing_keys:
            spawn_key = f"{base_key}-{suffix}"
            suffix += 1
        zone_data.setdefault("npc_spawns", []).append(
            {"key": spawn_key, "npc": npc_key, "vnum": overlay["vnum"]}
        )
        _write_zone(zone_path, zone_data)
        try:
            _reload_valid_overlays()
            imported = sync_authored_content(
                protocol.cursor.connection,
                zone_directory(),
                WORLD_OVERLAYS,
            )
        except Exception:
            protocol.cursor.connection.rollback()
            _write_zone(zone_path, original_zone_data)
            _reload_valid_overlays()
            raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to spawn NPC: {exc}".encode("utf-8"))
        return

    protocol.sendLine(
        (
            f"Spawned authored NPC {npc_key} as {spawn_key} in [{overlay['vnum']}]. "
            f"Created {imported['npc_spawns']} NPC spawn."
        ).encode("utf-8")
    )


def _authored_item_template_keys():
    """Return item template keys currently declared in zone JSON."""
    keys = set()
    for _, authored_zone in _all_authored_zones():
        keys.update(template["key"] for template in authored_zone.get("item_templates", []))
    return keys


def istat(protocol, item_key):
    """Inspect one globally keyed authored item template."""
    try:
        _, zone_data, template = _find_template("item", item_key)
        if not template:
            raise ValueError(f"Unknown authored item template: {item_key}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to inspect item template: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Item {template['key']}: {template['name']}".encode("utf-8"))
    protocol.sendLine(f"  Zone: {zone_data['name']}".encode("utf-8"))
    protocol.sendLine(f"  Description: {template['description']}".encode("utf-8"))
    protocol.sendLine(f"  Keywords: {', '.join(template.get('keywords', [])) or 'None'}".encode("utf-8"))
    protocol.sendLine(
        (
            f"  Type: {template.get('item_type', 'misc')} slot={template.get('equipment_slot') or 'None'} "
            f"damage={template.get('damage_bonus', 0)} throw={template.get('throw_damage', 0)} "
            f"nutrition={template.get('nutrition_restore', 0)} hydration={template.get('hydration_restore', 0)}"
        ).encode("utf-8")
    )


def iedit(protocol, item_key, field, value):
    """Create or edit authored item templates and synchronize definition metadata."""
    integer_fields = {
        "damage": "damage_bonus",
        "throw": "throw_damage",
        "nutrition": "nutrition_restore",
        "hydration": "hydration_restore",
    }
    try:
        if item_key == "create":
            parts = value.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError("Usage: iedit create <item_key> <name>")
            new_key, name = parts
            _validate_builder_key(new_key, "Item")
            name = _required_text(name, "Item name")
            if new_key in _authored_item_template_keys():
                raise ValueError(f"Authored item template already exists: {new_key}")
            _, zone_path, zone_data = _current_authored_room(protocol)
            original_zone_data = deepcopy(zone_data)
            zone_data.setdefault("item_templates", []).append(
                {
                    "key": new_key,
                    "name": name,
                    "description": f"{name} is unfinished authored content.",
                    "keywords": [new_key],
                    "item_type": "misc",
                }
            )
            _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data)
            protocol.sendLine(f"Created authored item template {new_key}: {name}.".encode("utf-8"))
            return

        zone_path, zone_data, template = _find_template("item", item_key)
        if not template:
            raise ValueError(f"Unknown authored item template: {item_key}")
        original_zone_data = deepcopy(zone_data)
        field = field.lower()
        if field == "name":
            template["name"] = _required_text(value, "Item name")
        elif field in {"desc", "description"}:
            template["description"] = _required_text(value, "Item description")
        elif field == "keywords":
            keywords = value.lower().split()
            if not keywords:
                raise ValueError("Item keywords cannot be empty.")
            template["keywords"] = keywords
        elif field == "type":
            template["item_type"] = value.lower()
        elif field == "slot":
            template["equipment_slot"] = None if value.lower() == "none" else value.lower()
        elif field == "use":
            template["use_text"] = _required_text(value, "Item use text")
        elif field in integer_fields:
            numeric_value = int(value)
            if numeric_value < 0:
                raise ValueError("Item numeric fields cannot be negative.")
            template[integer_fields[field]] = numeric_value
        else:
            raise ValueError("Item field must be name, desc, keywords, type, slot, use, damage, throw, nutrition, or hydration.")
        _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to edit item template: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Updated authored item {item_key} {field}.".encode("utf-8"))


def spawnitem(protocol, item_key):
    """Persist and import a finite item seed for the current authored room."""
    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        if item_key not in _authored_item_template_keys():
            raise ValueError(f"Unknown authored item template: {item_key}")
        original_zone_data = deepcopy(zone_data)
        existing_keys = {spawn["key"] for spawn in zone_data.get("item_spawns", [])}
        base_key = f"builder-{item_key}-{overlay['vnum']}"
        spawn_key = base_key
        suffix = 2
        while spawn_key in existing_keys:
            spawn_key = f"{base_key}-{suffix}"
            suffix += 1
        zone_data.setdefault("item_spawns", []).append(
            {"key": spawn_key, "item": item_key, "vnum": overlay["vnum"]}
        )
        _sync_zone_edit(protocol, zone_path, zone_data, original_zone_data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        protocol.sendLine(f"Unable to spawn item: {exc}".encode("utf-8"))
        return
    protocol.sendLine(f"Spawned authored item {item_key} as {spawn_key} in [{overlay['vnum']}].".encode("utf-8"))


def next_free_vnum(zone_data):
    """
    Finds the next available VNUM in the zone's range.
    """
    if not zone_data or "range" not in zone_data or "rooms" not in zone_data:
        logging.error("Invalid zone data.")
        return None
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None


def reverse_dir(direction):
    """
    Returns the reverse direction for linking rooms.
    """
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")


def shutdown(protocol, players_in_rooms=None):
    """
    Shuts down the server.
    """
    try:
        protocol.sendLine(b"Shutting down the server...")
        logging.info(f"User {protocol.username} initiated shutdown.")
        reactor.stop()
    except Exception as e:
        logging.error(f"Shutdown failed: {e}", exc_info=True)
        protocol.sendLine(f"Shutdown failed: {e}".encode('utf-8'))


def copyover(protocol, players_in_rooms=None):
    """Report that soft reboot is intentionally disabled for private alpha."""
    logging.info("User %s attempted disabled copyover.", protocol.username)
    protocol.sendLine(
        b"Copyover is disabled for now. Restart the server normally; players can reconnect safely."
    )


PLAYER_RESOURCE_FIELDS = {
    "health": ("health", None),
    "max_health": ("max_health", None),
    "maxhealth": ("max_health", None),
    "stamina": ("stamina", None),
    "max_stamina": ("max_stamina", None),
    "maxstamina": ("max_stamina", None),
    "chakra": ("chakra", None),
    "max_chakra": ("max_chakra", None),
    "maxchakra": ("max_chakra", None),
}
PLAYER_ATTRIBUTE_FIELDS = {
    field: (field, None)
    for field in ("strength", "dexterity", "agility", "intelligence", "wisdom")
}
PLAYER_BODY_FIELDS = {
    "nutrition": ("nutrition", 100),
    "hydration": ("hydration", 100),
    "fatigue": ("fatigue", 100),
}
PLAYER_TEXT_FIELDS = {
    "role": "role_type",
    "specialty": "role_type",
    "dojo": "dojo_alignment",
    "clan": "clan",
    "release": "natural_release",
}


def _online_player(username):
    """Return a connected protocol for a username when one exists."""
    return next(
        (
            player
            for player in online_players(players_in_rooms)
            if player.username.lower() == username.lower()
        ),
        None,
    )


def _player_row(protocol, username):
    return protocol.cursor.execute(
        """
        SELECT username, is_admin, role_type, clan, natural_release, dojo_alignment,
               health, max_health, stamina, max_stamina, chakra, max_chakra,
               strength, dexterity, agility, intelligence, wisdom,
               nutrition, hydration, fatigue, recovery_state, x, y
        FROM players
        WHERE username=? COLLATE NOCASE
        """,
        (username,),
    ).fetchone()


def pstat(protocol, username):
    """Display builder-facing persistent player state without sensitive fields."""
    player = _player_row(protocol, username)
    if not player:
        protocol.sendLine(f"Player not found: {username}".encode("utf-8"))
        return
    protocol.sendLine(f"Player {player['username']}".encode("utf-8"))
    protocol.sendLine(
        (
            f"  Admin: {'yes' if player['is_admin'] else 'no'}  "
            f"Specialty: {player['role_type']}  Clan: {player['clan']}  "
            f"Release: {player['natural_release']}"
        ).encode("utf-8")
    )
    protocol.sendLine(f"  Dojo: {player['dojo_alignment']}".encode("utf-8"))
    protocol.sendLine(
        (
            f"  Health: {player['health']}/{player['max_health']}  "
            f"Stamina: {player['stamina']}/{player['max_stamina']}  "
            f"Chakra: {player['chakra']}/{player['max_chakra']}"
        ).encode("utf-8")
    )
    protocol.sendLine(
        (
            f"  Attributes: strength={player['strength']} dexterity={player['dexterity']} "
            f"agility={player['agility']} intelligence={player['intelligence']} wisdom={player['wisdom']}"
        ).encode("utf-8")
    )
    protocol.sendLine(
        (
            f"  Body: nutrition={player['nutrition']} hydration={player['hydration']} "
            f"fatigue={player['fatigue']} recovery={player['recovery_state']}"
        ).encode("utf-8")
    )
    protocol.sendLine(f"  Location: ({player['x']}, {player['y']})".encode("utf-8"))


def _parse_boolean(value):
    normalized = value.strip().lower()
    if normalized in {"on", "yes", "true", "1"}:
        return 1
    if normalized in {"off", "no", "false", "0"}:
        return 0
    raise ValueError("Admin must be on or off.")


def _parse_bounded_integer(value, label, maximum=None):
    numeric_value = int(value)
    if numeric_value < 0 or (maximum is not None and numeric_value > maximum):
        limit = f" between 0 and {maximum}" if maximum is not None else " zero or greater"
        raise ValueError(f"{label} must be{limit}.")
    return numeric_value


def pset(protocol, username, field, value):
    """Set one curated persistent player field and refresh online protocol metadata."""
    player = _player_row(protocol, username)
    if not player:
        protocol.sendLine(f"Player not found: {username}".encode("utf-8"))
        return

    requested_field = field.lower()
    try:
        if requested_field == "admin":
            column = "is_admin"
            parsed_value = _parse_boolean(value)
        elif requested_field in PLAYER_TEXT_FIELDS:
            column = PLAYER_TEXT_FIELDS[requested_field]
            parsed_value = _required_text(value, requested_field.title())
        else:
            numeric_fields = {
                **PLAYER_RESOURCE_FIELDS,
                **PLAYER_ATTRIBUTE_FIELDS,
                **PLAYER_BODY_FIELDS,
            }
            if requested_field not in numeric_fields:
                raise ValueError(
                    "Player field must be admin, specialty, dojo, clan, release, "
                    "health, max_health, stamina, max_stamina, chakra, max_chakra, "
                    "strength, dexterity, agility, intelligence, wisdom, nutrition, hydration, or fatigue."
                )
            column, maximum = numeric_fields[requested_field]
            parsed_value = _parse_bounded_integer(value, column, maximum)
            resource_maximum = {
                "health": "max_health",
                "stamina": "max_stamina",
                "chakra": "max_chakra",
            }.get(column)
            if resource_maximum and parsed_value > player[resource_maximum]:
                raise ValueError(f"{column} cannot exceed {resource_maximum} ({player[resource_maximum]}).")

        protocol.cursor.execute(
            f"UPDATE players SET {column}=? WHERE username=? COLLATE NOCASE",
            (parsed_value, player["username"]),
        )
        if column == "max_health":
            protocol.cursor.execute(
                "UPDATE players SET health=MIN(health, max_health) WHERE username=? COLLATE NOCASE",
                (player["username"],),
            )
        elif column == "max_stamina":
            protocol.cursor.execute(
                "UPDATE players SET stamina=MIN(stamina, max_stamina) WHERE username=? COLLATE NOCASE",
                (player["username"],),
            )
        elif column == "max_chakra":
            protocol.cursor.execute(
                "UPDATE players SET chakra=MIN(chakra, max_chakra) WHERE username=? COLLATE NOCASE",
                (player["username"],),
            )
        protocol.cursor.connection.commit()
    except (TypeError, ValueError) as exc:
        protocol.cursor.connection.rollback()
        protocol.sendLine(f"Unable to set player: {exc}".encode("utf-8"))
        return
    except Exception as exc:
        protocol.cursor.connection.rollback()
        logging.error("Unable to set player field: %s", exc, exc_info=True)
        protocol.sendLine(b"Unable to set player field.")
        return

    online = _online_player(player["username"])
    if online:
        if column == "is_admin":
            online.is_admin = bool(parsed_value)
        elif column == "role_type":
            online.player_class = parsed_value
    protocol.sendLine(f"Set {column} of {player['username']} to {parsed_value}.".encode("utf-8"))


def setrole(protocol, username, role_type):
    """Backward-compatible wrapper for pset specialty."""
    pset(protocol, username, "specialty", role_type)


def setstat(protocol, username, stat, value):
    """Backward-compatible wrapper for pset numeric fields."""
    pset(protocol, username, stat, value)


def setdojo(protocol, username, dojo):
    """Backward-compatible wrapper for pset dojo."""
    pset(protocol, username, "dojo", dojo)

# Command registry
COMMANDS = {
    "createzone": CommandSpec("createzone", lambda protocol, rooms, raw, args: create_zone(protocol, *args), "createzone <zone_name> <start_vnum> <end_vnum>", "Create an authored zone.", permission="admin", min_args=3, max_args=3),
    "buildzone": CommandSpec("buildzone", lambda protocol, rooms, raw, args: buildzone(protocol, *args[:5], " ".join(args[5:])), "buildzone <zone_key> <start_vnum> <end_vnum> <x> <y> <room_title>", "Create, anchor, and enter a usable authored zone.", permission="admin", min_args=6),
    "zonelist": CommandSpec("zonelist", lambda protocol, rooms, raw, args: zonelist(protocol), "zonelist", "List authored zones and placement status.", permission="admin", max_args=0),
    "goto": CommandSpec("goto", lambda protocol, rooms, raw, args: goto(protocol, *args), "goto <vnum> | goto grid <x> <y> | goto player <name>", "Travel to an authored room, grid location, or online player.", permission="admin", min_args=1, max_args=3, args_validator=lambda args: (len(args) == 1 and args[0].isdigit()) or (len(args) == 3 and args[0].lower() == "grid" and args[1].lstrip("-").isdigit() and args[2].lstrip("-").isdigit()) or (len(args) == 2 and args[0].lower() == "player")),
    "zoneinfo": CommandSpec("zoneinfo", lambda protocol, rooms, raw, args: zoneinfo(protocol, args[0] if args else None), "zoneinfo [vnum]", "Inspect an authored overlay room.", permission="admin", max_args=1, args_validator=lambda args: not args or args[0].isdigit()),
    "placezone": CommandSpec("placezone", lambda protocol, rooms, raw, args: placezone(protocol, *args), "placezone <zone_file> <x> <y>", "Anchor a zone file on the world grid.", permission="admin", min_args=3, max_args=3, args_validator=lambda args: args[1].lstrip("-").isdigit() and args[2].lstrip("-").isdigit()),
    "reloadcontent": CommandSpec("reloadcontent", lambda protocol, rooms, raw, args: reloadcontent(protocol), "reloadcontent", "Reload authored JSON content into live state.", permission="admin", max_args=0),
    "dig": CommandSpec("dig", lambda protocol, rooms, raw, args: dig(protocol, args[0], " ".join(args[1:])), "dig <direction> <room_name>", "Create an authored room exit.", permission="admin", min_args=2),
    "roomdesc": CommandSpec("roomdesc", lambda protocol, rooms, raw, args: roomdesc(protocol, raw), "roomdesc <description>", "Replace the current authored room description.", permission="admin", min_args=1),
    "redit": CommandSpec("redit", lambda protocol, rooms, raw, args: redit(protocol, args[0], " ".join(args[1:])), "redit <title|desc|flag|exit> <value>", "Edit the current authored room.", permission="admin", min_args=2),
    "rstat": CommandSpec("rstat", lambda protocol, rooms, raw, args: rstat(protocol, args[0] if args else None), "rstat [vnum]", "Inspect authored room builder fields.", permission="admin", max_args=1, args_validator=lambda args: not args or args[0].isdigit()),
    "createnpc": CommandSpec("createnpc", lambda protocol, rooms, raw, args: createnpc(protocol, args[0], " ".join(args[1:])), "createnpc <npc_key> <name>", "Create a basic static authored NPC template.", permission="admin", min_args=2),
    "medit": CommandSpec("medit", lambda protocol, rooms, raw, args: medit(protocol, args[0], args[1], " ".join(args[2:])), "medit <npc_key> <field> <value>", "Edit an authored NPC template.", permission="admin", min_args=3),
    "mstat": CommandSpec("mstat", lambda protocol, rooms, raw, args: mstat(protocol, args[0]), "mstat <npc_key>", "Inspect an authored NPC template.", permission="admin", min_args=1, max_args=1),
    "spawnnpc": CommandSpec("spawnnpc", lambda protocol, rooms, raw, args: spawnnpc(protocol, args[0]), "spawnnpc <npc_key>", "Persist a spawn for an authored NPC template.", permission="admin", min_args=1, max_args=1),
    "iedit": CommandSpec("iedit", lambda protocol, rooms, raw, args: iedit(protocol, args[0], args[1] if len(args) > 1 else "", " ".join(args[2:]) if args[0] != "create" else " ".join(args[1:])), "iedit create <item_key> <name> | iedit <item_key> <field> <value>", "Create or edit an authored item template.", permission="admin", min_args=3),
    "istat": CommandSpec("istat", lambda protocol, rooms, raw, args: istat(protocol, args[0]), "istat <item_key>", "Inspect an authored item template.", permission="admin", min_args=1, max_args=1),
    "spawnitem": CommandSpec("spawnitem", lambda protocol, rooms, raw, args: spawnitem(protocol, args[0]), "spawnitem <item_key>", "Persist a finite authored item seed.", permission="admin", min_args=1, max_args=1),
    "shutdown": CommandSpec("shutdown", lambda protocol, rooms, raw, args: shutdown(protocol), "shutdown", "Stop the server.", permission="admin", max_args=0),
    "copyover": CommandSpec("copyover", lambda protocol, rooms, raw, args: copyover(protocol), "copyover", "Report the disabled soft-restart status.", permission="admin", max_args=0),
    "pstat": CommandSpec("pstat", lambda protocol, rooms, raw, args: pstat(protocol, args[0]), "pstat <username>", "Inspect persistent player state.", permission="admin", min_args=1, max_args=1),
    "pset": CommandSpec("pset", lambda protocol, rooms, raw, args: pset(protocol, args[0], args[1], " ".join(args[2:])), "pset <username> <field> <value>", "Set a validated persistent player field.", permission="admin", min_args=3),
    "setrole": CommandSpec("setrole", lambda protocol, rooms, raw, args: setrole(protocol, *args), "setrole <username> <role_type>", "Set a character role.", permission="admin", min_args=2, max_args=2),
    "setstat": CommandSpec("setstat", lambda protocol, rooms, raw, args: setstat(protocol, *args), "setstat <username> <stat> <value>", "Set a character stat.", permission="admin", min_args=3, max_args=3),
    "setdojo": CommandSpec("setdojo", lambda protocol, rooms, raw, args: setdojo(protocol, *args), "setdojo <username> <dojo>", "Set a character dojo alignment.", permission="admin", min_args=2, max_args=2),
}

