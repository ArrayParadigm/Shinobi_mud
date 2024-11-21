import os
import json
import logging

logging.info("utils imported")


def find_zone_by_vnum(vnum):
    """
    Finds the zone file containing a specific room VNUM.
    
    Args:
        vnum (int): The VNUM (Virtual Number) of the room to search for.

    Returns:
        str: The path to the zone file containing the VNUM, or None if not found.
    """
    zone_directory = os.path.join("zones")  # Directory containing all zone files
    try:
        for file_name in os.listdir(zone_directory):
            if file_name.endswith('.json'):  # Look for JSON files only
                with open(os.path.join(zone_directory, file_name), "r") as file:
                    zone_data = json.load(file)
                    # Check if the VNUM falls within the range defined in this zone
                    if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                        return os.path.join(zone_directory, file_name)
    except FileNotFoundError:
        logging.error(f"Zone directory '{zone_directory}' not found.")
    except Exception as e:
        logging.error(f"Error while searching for zone by VNUM: {e}")
    return None


def ensure_room_exists(vnum, protocol):
    """
    Ensures a room exists in a zone file, creating it if necessary.

    Args:
        vnum (int): The VNUM of the room to check or create.
        protocol (object): The protocol object representing the player.

    Returns:
        bool: True if the room exists or was successfully created, False otherwise.
    """
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Room not found in zone file.")
        return False

    try:
        with open(zone_file, "r") as file:
            zone_data = json.load(file)

        # If the room doesn't exist, initialize it with a default description and no exits
        if str(vnum) not in zone_data["rooms"]:
            zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
            with open(zone_file, "w") as file:
                json.dump(zone_data, file, indent=4)
            protocol.sendLine(b"Room initialized in zone file.")
        return True
    except Exception as e:
        logging.error(f"Error ensuring room exists for VNUM {vnum}: {e}")
        protocol.sendLine(b"Error processing room data.")
        return False


def next_free_vnum(zone_data):
    """
    Finds the next available VNUM in a zone.

    Args:
        zone_data (dict): The data of the zone to search.

    Returns:
        int: The next free VNUM, or None if no free VNUMs are available.
    """
    try:
        start, end = zone_data["range"]["start"], zone_data["range"]["end"]
        for vnum in range(start, end + 1):
            if str(vnum) not in zone_data["rooms"]:  # Check if the VNUM is unused
                return vnum
    except KeyError as e:
        logging.error(f"Invalid zone data structure: missing key {e}")
    except Exception as e:
        logging.error(f"Error finding next free VNUM: {e}")
    return None


def reverse_dir(direction):
    """
    Returns the reverse of a given direction.

    Args:
        direction (str): The direction to reverse (e.g., "north").

    Returns:
        str: The opposite direction (e.g., "south"), or an empty string if invalid.
    """
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")
