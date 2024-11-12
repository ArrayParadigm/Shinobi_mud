
import json
import os
import logging
from twisted.internet import reactor

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """Create a new zone as a JSON file in a subdirectory."""
    try:
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        zone_directory = os.path.join("zones")
        os.makedirs(zone_directory, exist_ok=True)
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")
        logging.info(f"Attempting to create zone file at: {zone_file_path}")

        if os.path.exists(zone_file_path):
            protocol.sendLine(b"Zone already exists.")
            logging.warning(f"Zone creation failed: {zone_file_path} already exists.")
            return

        zone_data = {
            "name": zone_name,
            "range": {"start": start_vnum, "end": end_vnum},
            "rooms": {}
        }

        with open(zone_file_path, "w") as zone_file:
            json.dump(zone_data, zone_file, indent=4)

        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum}.".encode('utf-8'))
        logging.info(f"Zone {zone_name} successfully created with range {start_vnum}-{end_vnum}.")

    except ValueError as ve:
        protocol.sendLine(b"VNUMs must be integers.")
        logging.error(f"ValueError in create_zone: {ve}")
    except Exception as e:
        protocol.sendLine(b"An error occurred while creating the zone.")
        logging.error(f"Unhandled exception in create_zone: {e}", exc_info=True)

def handle_shutdown(protocol):
    """Shut down the server safely."""
    protocol.sendLine(b"Shutting down the server...")
    reactor.stop()

def goto(protocol, vnum):
    """Move to a room by VNUM."""
    try:
        vnum = int(vnum)
        zone_file = find_zone_by_vnum(vnum)
        if not zone_file:
            protocol.sendLine(b"VNUM not found in any zone.")
            return

        with open(zone_file, "r") as file:
            zone_data = json.load(file)

        if str(vnum) not in zone_data["rooms"]:
            zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
            with open(zone_file, "w") as file:
                json.dump(zone_data, file, indent=4)

        protocol.current_room = vnum
        protocol.sendLine(f"Moved to room {vnum} in zone {zone_data['name']}".encode('utf-8'))
    except ValueError:
        protocol.sendLine(b"Invalid VNUM.")

def dig(protocol, direction, room_name):
    """Create a new room in the current zone and link it."""
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"Current room not found in zone.")
        return

    new_vnum = next_free_vnum(zone_data)
    if not new_vnum:
        protocol.sendLine(b"No free VNUMs in this zone.")
        return

    zone_data["rooms"][str(new_vnum)] = {"description": room_name, "exits": {}}
    zone_data["rooms"][str(vnum)]["exits"][direction] = new_vnum

    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

    protocol.sendLine(f"Room '{room_name}' created at {new_vnum} to the {direction}".encode('utf-8'))

def link(protocol, room_vnum, direction, target_vnum):
    """Link two rooms by creating a two-way exit."""
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(room_vnum) not in zone_data["rooms"] or str(target_vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"One or both rooms not found in zone.")
        return

    zone_data["rooms"][str(room_vnum)]["exits"][direction] = int(target_vnum)
    reverse_direction = {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")
    if reverse_direction:
        zone_data["rooms"][str(target_vnum)]["exits"][reverse_direction] = int(room_vnum)

    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

    protocol.sendLine(f"Rooms {room_vnum} and {target_vnum} linked via {direction}/{reverse_direction}".encode('utf-8'))

def remove_exit(protocol, direction):
    """Remove a specified exit from the current room."""
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"Current room not found in zone.")
        return

    room_exits = zone_data["rooms"][str(vnum)]["exits"]
    if direction in room_exits:
        del room_exits[direction]

        with open(zone_file, "w") as file:
            json.dump(zone_data, file, indent=4)

        protocol.sendLine(f"Exit {direction} removed from room {vnum}.".encode('utf-8'))
    else:
        protocol.sendLine(f"No {direction} exit exists to remove.".encode('utf-8'))

def list_rooms(protocol):
    """List all rooms in the current zone."""
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    protocol.sendLine(f"Rooms in zone '{zone_data['name']}':".encode('utf-8'))
    for room_id, room_data in zone_data["rooms"].items():
        exits = ", ".join(room_data["exits"].keys())
        protocol.sendLine(f"Room {room_id}: {room_data['description']} (Exits: {exits})".encode('utf-8'))

def find_zone_by_vnum(vnum):
    """Find the zone JSON file for a given VNUM."""
    zone_directory = os.path.join("zones")
    for file_name in os.listdir(zone_directory):
        if file_name.endswith('.json'):
            with open(os.path.join(zone_directory, file_name), "r") as file:
                zone_data = json.load(file)
                if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                    return os.path.join(zone_directory, file_name)
    return None

def next_free_vnum(zone_data):
    """Find the next available VNUM in the zone."""
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None

COMMANDS = {
    "shutdown": handle_shutdown,
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: goto <vnum>"),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args[0].split(maxsplit=1)) if len(args) == 1 else protocol.sendLine(b"Usage: dig <direction> <room_name>"),
    "link": lambda protocol, players_in_rooms, *args: link(protocol, *args[0].split(maxsplit=2)),
    "remove_exit": lambda protocol, players_in_rooms, *args: remove_exit(protocol, *args[0].strip()),
    "listrooms": lambda protocol, players_in_rooms: list_rooms(protocol),
}
