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


def dig(protocol, direction, room_name):
    """Create a coordinate-aware authored overlay room and reciprocal exit."""
    direction = direction.lower()
    if direction not in DIRECTION_OFFSETS:
        protocol.sendLine(b"Direction must be north, south, east, or west.")
        return

    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        room = zone_data["rooms"][str(overlay["vnum"])]
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
            "description": room_name.strip(),
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
        f"Dug {direction} to {room_name.strip()} [{new_vnum}] at {coordinates}.".encode("utf-8")
    )


def roomdesc(protocol, description):
    """Replace the current authored overlay room description."""
    try:
        overlay, zone_path, zone_data = _current_authored_room(protocol)
        original_zone_data = deepcopy(zone_data)
        zone_data["rooms"][str(overlay["vnum"])]["description"] = description.strip()
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


def createnpc(protocol, npc_key, npc_name):
    """Persist and import a basic static authored NPC template."""
    try:
        _, zone_path, zone_data = _current_authored_room(protocol)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", npc_key):
            raise ValueError("NPC key must use lowercase letters, numbers, and single hyphens.")
        if npc_key in _authored_npc_template_keys():
            raise ValueError(f"Authored NPC template already exists: {npc_key}")

        original_zone_data = deepcopy(zone_data)
        zone_data.setdefault("npc_templates", []).append(
            {
                "key": npc_key,
                "name": npc_name.strip(),
                "description": f"{npc_name.strip()} waits here.",
                "dialogue": f"{npc_name.strip()} has nothing to say yet.",
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

    protocol.sendLine(f"Created authored NPC template {npc_key}: {npc_name.strip()}.".encode("utf-8"))


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

def setrole(protocol, username, role_type):
    """
    Sets the role of a player.
    """
    try:
        protocol.cursor.execute("UPDATE players SET role_type=? WHERE username=?", (role_type, username))
        protocol.cursor.connection.commit()
        protocol.sendLine(f"Set role of {username} to {role_type}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set role: {e}".encode('utf-8'))


def setstat(protocol, username, stat, value):
    """
    Sets a player's stat to a given value.
    """
    try:
        if stat not in ('health', 'max_health', 'stamina', 'max_stamina', 'chakra', 'max_chakra', 'strength', 'dexterity', 'agility', 'intelligence', 'wisdom'):
            protocol.sendLine(b"Invalid stat.")
            return
        protocol.cursor.execute(f"UPDATE players SET {stat}=? WHERE username=?", (int(value), username))
        protocol.cursor.connection.commit()
        protocol.sendLine(f"Set {stat} of {username} to {value}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set stat: {e}".encode('utf-8'))


def setdojo(protocol, username, dojo):
    """
    Sets a player's dojo alignment.
    """
    try:
        protocol.cursor.execute("UPDATE players SET dojo_alignment=? WHERE username=?", (dojo, username))
        protocol.cursor.connection.commit()
        protocol.sendLine(f"Set dojo of {username} to {dojo}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set dojo: {e}".encode('utf-8'))

# Command registry
COMMANDS = {
    "createzone": CommandSpec("createzone", lambda protocol, rooms, raw, args: create_zone(protocol, *args), "createzone <zone_name> <start_vnum> <end_vnum>", "Create an authored zone.", permission="admin", min_args=3, max_args=3),
    "goto": CommandSpec("goto", lambda protocol, rooms, raw, args: goto(protocol, *args), "goto <vnum> | goto grid <x> <y> | goto player <name>", "Travel to an authored room, grid location, or online player.", permission="admin", min_args=1, max_args=3, args_validator=lambda args: (len(args) == 1 and args[0].isdigit()) or (len(args) == 3 and args[0].lower() == "grid" and args[1].lstrip("-").isdigit() and args[2].lstrip("-").isdigit()) or (len(args) == 2 and args[0].lower() == "player")),
    "zoneinfo": CommandSpec("zoneinfo", lambda protocol, rooms, raw, args: zoneinfo(protocol, args[0] if args else None), "zoneinfo [vnum]", "Inspect an authored overlay room.", permission="admin", max_args=1, args_validator=lambda args: not args or args[0].isdigit()),
    "placezone": CommandSpec("placezone", lambda protocol, rooms, raw, args: placezone(protocol, *args), "placezone <zone_file> <x> <y>", "Anchor a zone file on the world grid.", permission="admin", min_args=3, max_args=3, args_validator=lambda args: args[1].lstrip("-").isdigit() and args[2].lstrip("-").isdigit()),
    "reloadcontent": CommandSpec("reloadcontent", lambda protocol, rooms, raw, args: reloadcontent(protocol), "reloadcontent", "Reload authored JSON content into live state.", permission="admin", max_args=0),
    "dig": CommandSpec("dig", lambda protocol, rooms, raw, args: dig(protocol, args[0], " ".join(args[1:])), "dig <direction> <room_name>", "Create an authored room exit.", permission="admin", min_args=2),
    "roomdesc": CommandSpec("roomdesc", lambda protocol, rooms, raw, args: roomdesc(protocol, raw), "roomdesc <description>", "Replace the current authored room description.", permission="admin", min_args=1),
    "createnpc": CommandSpec("createnpc", lambda protocol, rooms, raw, args: createnpc(protocol, args[0], " ".join(args[1:])), "createnpc <npc_key> <name>", "Create a basic static authored NPC template.", permission="admin", min_args=2),
    "spawnnpc": CommandSpec("spawnnpc", lambda protocol, rooms, raw, args: spawnnpc(protocol, args[0]), "spawnnpc <npc_key>", "Persist a spawn for an authored NPC template.", permission="admin", min_args=1, max_args=1),
    "shutdown": CommandSpec("shutdown", lambda protocol, rooms, raw, args: shutdown(protocol), "shutdown", "Stop the server.", permission="admin", max_args=0),
    "copyover": CommandSpec("copyover", lambda protocol, rooms, raw, args: copyover(protocol), "copyover", "Report the disabled soft-restart status.", permission="admin", max_args=0),
    "setrole": CommandSpec("setrole", lambda protocol, rooms, raw, args: setrole(protocol, *args), "setrole <username> <role_type>", "Set a character role.", permission="admin", min_args=2, max_args=2),
    "setstat": CommandSpec("setstat", lambda protocol, rooms, raw, args: setstat(protocol, *args), "setstat <username> <stat> <value>", "Set a character stat.", permission="admin", min_args=3, max_args=3),
    "setdojo": CommandSpec("setdojo", lambda protocol, rooms, raw, args: setdojo(protocol, *args), "setdojo <username> <dojo>", "Set a character dojo alignment.", permission="admin", min_args=2, max_args=2),
}

