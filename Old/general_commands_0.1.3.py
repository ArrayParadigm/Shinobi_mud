
from admin_commands import find_zone_by_vnum
import json

def handle_look(protocol, players_in_rooms=None):
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    room = zone_data["rooms"].get(str(vnum))
    if not room:
        protocol.sendLine(b"Room not found.")
        return

    description = room["description"]
    exits = ", ".join(room["exits"].keys()) or "None"
    protocol.sendLine(f"Room {vnum}: {description}".encode('utf-8'))
    protocol.sendLine(f"Exits: {exits}".encode('utf-8'))

def handle_movement(protocol, direction):
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    current_room = zone_data["rooms"].get(str(vnum))
    if not current_room:
        protocol.sendLine(b"Current room not found.")
        return

    next_vnum = current_room["exits"].get(direction)
    if not next_vnum:
        protocol.sendLine(b"No exit in that direction.")
        return

    protocol.current_room = next_vnum
    protocol.sendLine(f"Moved to room {next_vnum}.".encode('utf-8'))
    handle_look(protocol)

COMMANDS = {
    "look": handle_look,
    "north": lambda protocol, players_in_rooms=None: handle_movement(protocol, "north"),
    "south": lambda protocol, players_in_rooms=None: handle_movement(protocol, "south"),
    "east": lambda protocol, players_in_rooms=None: handle_movement(protocol, "east"),
    "west": lambda protocol, players_in_rooms=None: handle_movement(protocol, "west"),
}
