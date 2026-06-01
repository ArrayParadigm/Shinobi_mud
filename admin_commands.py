import json
import os
import logging
import sys
from command_system import CommandSpec
from twisted.internet import reactor
from shinobi_mud import UTILITIES

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

# TODO: fix "goto" to allow navigation to specific coordinations and players.
def goto(protocol, vnum):
    """
    Reserved for the future coordinate-overlay builder workflow.
    """
    protocol.sendLine(b"VNUM goto is unavailable until grid overlays are enabled.")


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
    """
    Soft reboot (copyover) while saving minimal player state.
    """
    try:
        protocol.sendLine(b"Initiating copyover... Please hold on.")
        logging.info(f"User {protocol.username} initiated copyover.")

        # Save player room and username
        with open("copyover_state.json", "w") as f:
            state_data = {
                "players": [
                    {
                        "username": protocol.username,
                        "x": protocol.x,
                        "y": protocol.y,
                    }
                ]
            }
            json.dump(state_data, f)

        args = sys.argv[:]
        args.insert(0, sys.executable)
        os.execv(sys.executable, args)
    except Exception as e:
        logging.error(f"Copyover failed: {e}", exc_info=True)
        protocol.sendLine(b"Copyover failed. Please contact an admin.")

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
    "goto": CommandSpec("goto", lambda protocol, rooms, raw, args: goto(protocol, args[0]), "goto <room_id>", "Travel to an authored room.", permission="admin", min_args=1, max_args=1, args_validator=lambda args: args[0].isdigit()),
    "dig": CommandSpec("dig", lambda protocol, rooms, raw, args: dig(protocol, args[0], " ".join(args[1:])), "dig <direction> <room_name>", "Create an authored room exit.", permission="admin", min_args=2),
    "shutdown": CommandSpec("shutdown", lambda protocol, rooms, raw, args: shutdown(protocol), "shutdown", "Stop the server.", permission="admin", max_args=0),
    "copyover": CommandSpec("copyover", lambda protocol, rooms, raw, args: copyover(protocol), "copyover", "Restart the server while retaining player state.", permission="admin", max_args=0),
    "setrole": CommandSpec("setrole", lambda protocol, rooms, raw, args: setrole(protocol, *args), "setrole <username> <role_type>", "Set a character role.", permission="admin", min_args=2, max_args=2),
    "setstat": CommandSpec("setstat", lambda protocol, rooms, raw, args: setstat(protocol, *args), "setstat <username> <stat> <value>", "Set a character stat.", permission="admin", min_args=3, max_args=3),
    "setdojo": CommandSpec("setdojo", lambda protocol, rooms, raw, args: setdojo(protocol, *args), "setdojo <username> <dojo>", "Set a character dojo alignment.", permission="admin", min_args=2, max_args=2),
}

