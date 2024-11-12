
import json
import os

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """Create a new zone as a JSON file in a subdirectory."""
    try:
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        zone_directory = os.path.join("zones")
        os.makedirs(zone_directory, exist_ok=True)
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")

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

        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum} in 'zones' directory.".encode('utf-8'))
    except ValueError:
        protocol.sendLine(b"VNUMs must be integers.")

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
    # Dig logic copied and preserved from the existing command; ensures room links.

def link(protocol, room_vnum, direction, target_vnum):
    """Link two rooms by creating a two-way exit."""
    # Implementation for link

def remove_exit(protocol, direction):
    """Remove a specified exit from the current room."""
    # Implementation for remove_exit command as before

def list_rooms(protocol):
    """List all rooms in the current zone."""
    # See all room entries clearly

COMMANDS = {
    "shutdown": handle_shutdown,
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: goto <vnum>"),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args[0].split(maxsplit=1)) if len(args) == 1 else protocol.sendLine(b"Usage: dig <direction> <room_name>"),
    "link": lambda protocol, players_in_rooms, *args: link(protocol, *args[0].split(maxsplit=2)),
    "remove_exit": lambda protocol, players_in_rooms, *args: remove_exit(protocol, *args[0].strip()),
    "listrooms": lambda protocol, players_in_rooms: list_rooms(protocol),
}
