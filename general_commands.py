import json
import logging
from shinobi_mud import UTILITIES

logging.info("general_commands imported")


def handle_look(player, players_in_rooms=None):
    vnum = player.current_room
    logging.debug(f"UTILITIES in general_commands: {UTILITIES.keys()}")
    
    # Use UTILITIES reference for WORLD_MAP and render_open_land
    WORLD_MAP = UTILITIES.get("WORLD_MAP")
    render_open_land = UTILITIES.get("render_open_land")

    if player.in_zone:
        render_room(player)  # Render room if in zone
    else:
        if not render_open_land:
            player.sendLine(b"Error: render_open_land function is not available.")
            return
        player.sendLine(render_open_land(player.x, player.y, radius=1).encode("utf-8"))

    zone_file = UTILITIES["find_zone_by_vnum"](vnum)
    if not zone_file:
        player.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    room = zone_data["rooms"].get(str(vnum))
    if not room:
        player.sendLine(b"Room not found.")
        return

    description = room.get("description", "An empty room.")
    exits = ", ".join(room.get("exits", {}).keys()) or "None"
    player.sendLine(f"Room {vnum}: {description}".encode("utf-8"))
    player.sendLine(f"Exits: {exits}".encode("utf-8"))

def check_zone_entry(player):
    WORLD_MAP = UTILITIES["WORLD_MAP"]  # Access WORLD_MAP through UTILITIES
    current_cell = WORLD_MAP[player.y][player.x]
    if current_cell.isdigit():  # Check if the cell represents a VNUM
        player.in_zone = True
        player.current_room = int(current_cell)
        render_room(player)
    else:
        player.in_zone = False
        player.sendLine(UTILITIES["render_open_land"](player.x, player.y).encode("utf-8"))

def handle_movement(player, direction):
    dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[direction]
    WORLD_MAP = UTILITIES["load_world_map"]()  # Access WORLD_MAP through UTILITIES
    new_x, new_y = player.x + dx, player.y + dy

    if 0 <= new_y < len(WORLD_MAP) and 0 <= new_x < len(WORLD_MAP[0]):
        player.x, player.y = new_x, new_y
        check_zone_entry(player)  # Update zone or open land status
    else:
        player.sendLine(b"You can't go that way.")

def handle_status(player, players_in_rooms=None):
    try:
        player.cursor.execute(
            "SELECT health, stamina, chakra, strength, dexterity, agility, intelligence, wisdom, dojo_alignment "
            "FROM players WHERE username=?",
            (player.username,)
        )
        stats = player.cursor.fetchone()
        if stats:
            player.sendLine(f"Stats for {player.username}:".encode('utf-8'))
            player.sendLine(f"Health: {stats[0]}, Stamina: {stats[1]}, Chakra: {stats[2]}".encode('utf-8'))
            player.sendLine(f"Strength: {stats[3]}, Dexterity: {stats[4]}, Agility: {stats[5]}".encode('utf-8'))
            player.sendLine(f"Intelligence: {stats[6]}, Wisdom: {stats[7]}, Dojo Alignment: {stats[8]}".encode('utf-8'))
        else:
            player.sendLine(b"No stats found for your character.")
    except Exception as e:
        logging.error(f"Error retrieving stats for {player.username}: {e}", exc_info=True)
        player.sendLine(f"Error retrieving stats: {e}".encode('utf-8'))

def handle_survey(player):
    if player.in_zone:
        player.sendLine(b"You cannot survey while inside a zone.")
    else:
        player.sendLine(UTILITIES["render_open_land"](player.x, player.y, radius=5).encode("utf-8"))

COMMANDS = {
    "look": lambda player, players_in_rooms, raw_args, split_args: handle_look(player, players_in_rooms),
    "north": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "north"),
    "south": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "south"),
    "east": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "east"),
    "west": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "west"),
    "status": lambda player, players_in_rooms, raw_args, split_args: handle_status(player, players_in_rooms),
    "survey": lambda player, players_in_rooms, raw_args, split_args: handle_survey(player),
    
}

