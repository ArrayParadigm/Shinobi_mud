import json
import logging
from shinobi_mud import UTILITIES

logging.info("general_commands imported")


def handle_look(player, players_in_rooms=None):
    """Displays a 41x21 map centered on the player's current position."""
    WORLD_MAP = UTILITIES.get("WORLD_MAP")
    if not WORLD_MAP:
        player.sendLine(b"Error: World map is not available.")
        return

    # Render the map using render_open_land
    try:
        render_open_land = UTILITIES["render_open_land"]
        map_view = render_open_land(player.x, player.y, world_map=WORLD_MAP)
        player.sendLine(map_view.encode("utf-8"))  # Send the rendered map to the player
        player.sendLine(b"You see open land around you.")
    except KeyError:
        player.sendLine(b"Error: Map rendering function is not available.")
    except Exception as e:
        logging.error(f"Error during map rendering: {e}", exc_info=True)
        player.sendLine(b"An error occurred while rendering the map.")

def check_zone_entry(player):
    """Checks if the player has entered a zone and updates their status, temporarily bypassing VNUM transitions."""
    WORLD_MAP = UTILITIES["WORLD_MAP"]
    current_cell = WORLD_MAP[player.y][player.x]
    
    # Debugging information for movement and map cells
    logging.debug(f"Player moved to ({player.x}, {player.y}). Current cell: {current_cell}.")
    logging.debug(f"In zone: {player.in_zone}")

    # Temporarily bypass numeric VNUMs
    if current_cell.isdigit():
        logging.debug("Numeric VNUM detected, but bypassing room transition.")
        player.sendLine(b"You are bypassing VNUM-based room transitions.")
        player.in_zone = False
        return

    # Default: Show the open map view
    player.in_zone = False
    player.sendLine(render_open_land(player.x, player.y, world_map=WORLD_MAP).encode("utf-8"))


def handle_movement(player, direction):
    """Handles player movement in a specified direction."""
    directions = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
    dx, dy = directions.get(direction, (0, 0))
    new_x, new_y = player.x + dx, player.y + dy

    world_map = UTILITIES.get("WORLD_MAP")
    if not world_map:
        player.sendLine(b"Error: World map is unavailable.")
        return

    # Check boundaries
    if 0 <= new_x < len(world_map[0]) and 0 <= new_y < len(world_map):
        player.x, player.y = new_x, new_y
        map_view = UTILITIES["render_open_land"](player.x, player.y, world_map=world_map)
        player.sendLine(map_view.encode("utf-8"))
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
    "status": lambda player, players_in_rooms, raw_args, split_args: handle_status(player, players_in_rooms),
    "survey": lambda player, players_in_rooms, raw_args, split_args: handle_survey(player),
    "north": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "north"),
    "south": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "south"),
    "east": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "east"),
    "west": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "west"),


    
}

