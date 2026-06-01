import os
import json
import logging
import items

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
        
def overlay_zone(zone_data, anchor_x, anchor_y, overlays=None):
    """Attach optional authored room metadata to world coordinates."""
    overlays = overlays if overlays is not None else {}
    for vnum, room_data in zone_data["rooms"].items():
        x_offset = room_data.get("x_offset", 0)
        y_offset = room_data.get("y_offset", 0)
        x, y = anchor_x + x_offset, anchor_y + y_offset
        if (x, y) in overlays:
            raise ValueError(f"Multiple authored rooms overlap at ({x}, {y}).")
        overlays[(x, y)] = {
            "zone_name": zone_data["name"],
            "vnum": int(vnum),
            "room": room_data,
        }
    return overlays


def find_overlay_by_vnum(overlays, vnum):
    """Return the coordinate and overlay metadata for an authored room VNUM."""
    target_vnum = int(vnum)
    for coordinates, overlay in overlays.items():
        if overlay["vnum"] == target_vnum:
            return coordinates, overlay
    return None

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

def load_world_map(filename="world.map"):
    with open(filename, "r") as file:
        return [list(line.strip()) for line in file.readlines()]

def preload_zones_with_anchors(overlays=None, zones_directory="zones"):
    """Load zone metadata into a coordinate overlay registry."""
    overlays = overlays if overlays is not None else {}
    loaded_overlays = {}
    
    for zone_file in os.listdir(zones_directory):
        if zone_file.endswith(".json"):
            with open(os.path.join(zones_directory, zone_file), "r") as file:
                zone_data = json.load(file)
                anchor = zone_data.get("anchor")
                if not anchor:
                    continue
                overlay_zone(zone_data, int(anchor["x"]), int(anchor["y"]), loaded_overlays)
    overlays.clear()
    overlays.update(loaded_overlays)
    return overlays

def reverse_dir(direction):
    """
    Returns the reverse of a given direction.

    Args:
        direction (str): The direction to reverse (e.g., "north").

    Returns:
        str: The opposite direction (e.g., "south"), or an empty string if invalid.
    """
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")

def render_open_land(
    player_x,
    player_y,
    world_map=None,
    overlays=None,
    width_radius=20,
    height_radius=10,
):
    """Renders a portion of the world map centered around the player's position."""
    if world_map is None:
        raise ValueError("A valid world_map must be provided.")
    
    visible_map = []

    for y in range(player_y - height_radius, player_y + height_radius + 1):
        row = ""
        for x in range(player_x - width_radius, player_x + width_radius + 1):
            if 0 <= y < len(world_map) and 0 <= x < len(world_map[0]):
                if x == player_x and y == player_y:
                    row += "P"  # Mark the player
                elif overlays and (x, y) in overlays:
                    row += "#"  # Mark authored content without mutating terrain
                else:
                    row += world_map[y][x]
            else:
                row += "?"  # Out-of-bounds area
        visible_map.append(row)

    visible_map.append("Legend: P=you  #=authored area")
    return "\n".join(visible_map)

def render_room(player, overlays=None):
    """Render optional authored content attached to a player's coordinate."""
    overlay = (overlays or {}).get((player.x, player.y))
    if not overlay:
        player.sendLine(b"You see open land around you.")
    else:
        room = overlay["room"]
        exits = ", ".join(room.get("exits", {}).keys()) or "None"
        description = room.get("description", "No description.")
        player.sendLine(
            f"{overlay['zone_name']} [{overlay['vnum']}]\n{description}\nExits: {exits}".encode("utf-8")
        )

    visible_items = items.room_items(player.cursor, player.x, player.y)
    if visible_items:
        player.sendLine(
            f"Items here: {items.format_item_names(visible_items)}".encode("utf-8")
        )
