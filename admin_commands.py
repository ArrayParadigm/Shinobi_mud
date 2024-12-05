import json
import os
import logging
import sys
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
    Moves the player to the specified VNUM, creating the room if necessary.
    """
    try:
        vnum = int(vnum)
        if "find_zone_by_vnum" not in UTILITIES or "ensure_room_exists" not in UTILITIES:
            protocol.sendLine(b"Utilities not properly configured.")
            return

        zone_file = UTILITIES["find_zone_by_vnum"](vnum)
        if not UTILITIES["ensure_room_exists"](vnum, protocol):
            return

        with open(zone_file, "r") as file:
            zone_data = json.load(file)

        if str(vnum) not in zone_data["rooms"]:
            protocol.sendLine(b"Room not found. Initializing empty room.")
            zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
            with open(zone_file, "w") as file:
                json.dump(zone_data, file, indent=4)

        protocol.current_room = vnum
        protocol.sendLine(f"Moved to room {vnum} in zone {zone_data['name']}".encode('utf-8'))

    except ValueError:
        protocol.sendLine(b"Invalid VNUM.")
    except Exception as e:
        logging.error(f"Error in goto: {e}", exc_info=True)
        protocol.sendLine(f"Error: {e}".encode('utf-8'))


def dig(protocol, direction, room_name):
    """
    Creates a new room in the specified direction and links it to the current room.
    """
    if direction not in ["north", "south", "east", "west"]:
        protocol.sendLine(b"Invalid direction.")
        return
    if "find_zone_by_vnum" not in UTILITIES:
        protocol.sendLine(b"Utilities not properly configured.")
        return

    vnum = protocol.current_room
    zone_file = UTILITIES["find_zone_by_vnum"](vnum)

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"Current room not found in zone.")
        return

    new_vnum = next_free_vnum(zone_data)
    if not new_vnum:
        protocol.sendLine(b"No free VNUMs in this zone.")
        return

    # Create and link new room
    zone_data["rooms"][str(new_vnum)] = {"description": room_name, "exits": {reverse_dir(direction): vnum}}
    zone_data["rooms"][str(vnum)]["exits"][direction] = new_vnum

    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

    protocol.sendLine(f"Room '{room_name}' created at {new_vnum} to the {direction}".encode('utf-8'))


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
                        "room": protocol.current_room,
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
        cursor.execute("UPDATE players SET role_type=? WHERE username=?", (int(role_type), username))
        conn.commit()
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
        cursor.execute(f"UPDATE players SET {stat}=? WHERE username=?", (int(value), username))
        conn.commit()
        protocol.sendLine(f"Set {stat} of {username} to {value}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set stat: {e}".encode('utf-8'))


def setdojo(protocol, username, dojo):
    """
    Sets a player's dojo alignment.
    """
    try:
        cursor.execute("UPDATE players SET dojo_alignment=? WHERE username=?", (dojo, username))
        conn.commit()
        protocol.sendLine(f"Set dojo of {username} to {dojo}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set dojo: {e}".encode('utf-8'))

# Command registry
COMMANDS = {
    "createzone": lambda protocol, players_in_rooms, raw_args, split_args: create_zone(protocol, *split_args) if len(split_args) == 3 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
    "goto": lambda protocol, players_in_rooms, raw_args, split_args: goto(protocol, split_args[0]) if len(split_args) >= 1 and split_args[0].isdigit() else protocol.sendLine(b"Usage: goto <room_id>"),
    "dig": lambda protocol, players_in_rooms, raw_args, split_args: dig(protocol, *split_args) if len(split_args) >= 2 else protocol.sendLine(b"Usage: dig <direction> <room_name>"),
    "shutdown": lambda protocol, players_in_rooms, raw_args, split_args: shutdown(protocol),
    "copyover": lambda protocol, players_in_rooms, raw_args, split_args: copyover(protocol),
    "setrole": lambda protocol, players_in_rooms, raw_args, split_args: setrole(protocol, *split_args) if len(split_args) == 2 else protocol.sendLine(b"Usage: setrole <username> <role_type>"),
    "setstat": lambda protocol, players_in_rooms, raw_args, split_args: setstat(protocol, *split_args) if len(split_args) == 3 else protocol.sendLine(b"Usage: setstat <username> <stat> <value>"),
    "setdojo": lambda protocol, players_in_rooms, raw_args, split_args: setdojo(protocol, *split_args) if len(split_args) == 2 else protocol.sendLine(b"Usage: setdojo <username> <dojo>"),
}

