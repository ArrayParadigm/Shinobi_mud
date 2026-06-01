import json
import os
import logging
from command_system import CommandSpec
from locations import is_within_bounds, online_players, teleport_player
from twisted.internet import reactor
from shinobi_mud import UTILITIES, WORLD_MAP, WORLD_OVERLAYS, players_in_rooms

logging.info("admin_commands imported")


def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """
    Creates a new zone with a specified range of VNUMs.
    """
    try:
        if not zone_name.strip():
            protocol.sendLine(b"Zone name cannot be empty.")
            return

        start_vnum, end_vnum = int(start_vnum), int(end_vnum)

        zone_directory = os.path.join("zones")
        os.makedirs(zone_directory, exist_ok=True)
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")
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
    zone_path = os.path.join("zones", safe_name)
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
        UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS)
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
            UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS)
        protocol.sendLine(f"Unable to place zone: {exc}".encode("utf-8"))
        return

    protocol.sendLine(
        f"Placed {zone_data['name']} at ({anchor_x}, {anchor_y}) with {len(zone_data['rooms'])} overlay rooms.".encode("utf-8")
    )


def dig(protocol, direction, room_name):
    """
    Reserved for the future coordinate-overlay builder workflow.
    """
    protocol.sendLine(b"VNUM dig is unavailable until grid overlays are enabled.")


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
        protocol.cursor.execute("UPDATE players SET role_type=? WHERE username=?", (int(role_type), username))
        protocol.cursor.connection.commit()
        protocol.sendLine(f"Set role of {username} to {role_type}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set role: {e}".encode('utf-8'))


def setstat(protocol, username, stat, value):
    """
    Sets a player's stat to a given value.
    """
    try:
        if stat not in ('health', 'stamina', 'chakra', 'strength', 'dexterity', 'agility', 'intelligence', 'wisdom'):
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
    "dig": CommandSpec("dig", lambda protocol, rooms, raw, args: dig(protocol, args[0], " ".join(args[1:])), "dig <direction> <room_name>", "Create an authored room exit.", permission="admin", min_args=2),
    "shutdown": CommandSpec("shutdown", lambda protocol, rooms, raw, args: shutdown(protocol), "shutdown", "Stop the server.", permission="admin", max_args=0),
    "copyover": CommandSpec("copyover", lambda protocol, rooms, raw, args: copyover(protocol), "copyover", "Report the disabled soft-restart status.", permission="admin", max_args=0),
    "setrole": CommandSpec("setrole", lambda protocol, rooms, raw, args: setrole(protocol, *args), "setrole <username> <role_type>", "Set a character role.", permission="admin", min_args=2, max_args=2),
    "setstat": CommandSpec("setstat", lambda protocol, rooms, raw, args: setstat(protocol, *args), "setstat <username> <stat> <value>", "Set a character stat.", permission="admin", min_args=3, max_args=3),
    "setdojo": CommandSpec("setdojo", lambda protocol, rooms, raw, args: setdojo(protocol, *args), "setdojo <username> <dojo>", "Set a character dojo alignment.", permission="admin", min_args=2, max_args=2),
}

