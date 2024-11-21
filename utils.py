import os
import json
import logging
logging.info("utils imported")


def find_zone_by_vnum(vnum):
    """Finds the zone file containing a specific room VNUM."""
    zone_directory = os.path.join("zones")
    for file_name in os.listdir(zone_directory):
        if file_name.endswith('.json'):
            with open(os.path.join(zone_directory, file_name), "r") as file:
                zone_data = json.load(file)
                if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                    return os.path.join(zone_directory, file_name)
    return None

def ensure_room_exists(vnum, protocol):
    """Ensures a room exists in a zone file, initializing it if necessary."""
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Room not found in zone file.")
        return False

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
        with open(zone_file, "w") as file:
            json.dump(zone_data, file, indent=4)
        protocol.sendLine(b"Room initialized in zone file.")

    return True

def next_free_vnum(zone_data):
    """Finds the next free VNUM in a zone."""
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None

def reverse_dir(direction):
    """Returns the reverse of a given direction."""
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")
