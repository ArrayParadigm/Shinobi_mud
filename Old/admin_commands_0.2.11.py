
import json
import os
import logging
from twisted.internet import reactor

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    try:
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

def goto(protocol, vnum):
    try:
        vnum = int(vnum)
        zone_file = find_zone_by_vnum(vnum)
        if not zone_file:
            protocol.sendLine(b"VNUM not found in any zone.")
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

def dig(protocol, direction, room_name):
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

    # Create and link new room
    zone_data["rooms"][str(new_vnum)] = {"description": room_name, "exits": {reverse_dir(direction): vnum}}
    zone_data["rooms"][str(vnum)]["exits"][direction] = new_vnum

    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

    protocol.sendLine(f"Room '{room_name}' created at {new_vnum} to the {direction}".encode('utf-8'))

def find_zone_by_vnum(vnum):
    zone_directory = os.path.join("zones")
    for file_name in os.listdir(zone_directory):
        if file_name.endswith('.json'):
            with open(os.path.join(zone_directory, file_name), "r") as file:
                zone_data = json.load(file)
                if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                    return os.path.join(zone_directory, file_name)
    return None

def next_free_vnum(zone_data):
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None

def reverse_dir(direction):
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")

COMMANDS = {
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args[0].split()),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args[0].split(maxsplit=1)),
}
