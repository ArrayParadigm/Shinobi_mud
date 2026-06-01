import json
import logging
from locations import LocationPersistenceError, get_location, move_player, online_players
from shinobi_mud import UTILITIES, WORLD_OVERLAYS, players_in_rooms

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
        map_view = render_open_land(
            player.x,
            player.y,
            world_map=WORLD_MAP,
            overlays=WORLD_OVERLAYS,
        )
        player.sendLine(map_view.encode("utf-8"))  # Send the rendered map to the player
        location = get_location(WORLD_MAP, player.x, player.y, WORLD_OVERLAYS)
        overlay = location["overlay"]
        if overlay:
            player.sendLine(f"You are in {overlay['zone_name']}.".encode("utf-8"))
        else:
            player.sendLine(b"You see open land around you.")
        player.list_players_in_room()
    except KeyError:
        player.sendLine(b"Error: Map rendering function is not available.")
    except Exception as e:
        logging.error(f"Error during map rendering: {e}", exc_info=True)
        player.sendLine(b"An error occurred while rendering the map.")

def handle_movement(player, direction):
    """Handles player movement in a specified direction."""
    world_map = UTILITIES.get("WORLD_MAP")
    if not world_map:
        player.sendLine(b"Error: World map is unavailable.")
        return

    try:
        if move_player(player, direction, world_map, players_in_rooms):
            map_view = UTILITIES["render_open_land"](
                player.x,
                player.y,
                world_map=world_map,
                overlays=WORLD_OVERLAYS,
            )
            player.sendLine(map_view.encode("utf-8"))
        else:
            player.sendLine(b"You can't go that way.")
    except LocationPersistenceError:
        logging.warning("Movement save blocked for player %s.", player.username)
        player.sendLine(b"Movement could not be saved. Please try again.")

def handle_score(player, players_in_rooms=None):
    """Display the player's current character sheet."""
    try:
        player.cursor.execute(
            "SELECT health, stamina, chakra, strength, dexterity, agility, intelligence, wisdom, dojo_alignment "
            "FROM players WHERE username=?",
            (player.username,)
        )
        stats = player.cursor.fetchone()
        if stats:
            player.sendLine(f"Score for {player.username}".encode("utf-8"))
            player.sendLine(b"--------------------")
            player.sendLine(f"Health: {stats[0]}  Stamina: {stats[1]}  Chakra: {stats[2]}".encode("utf-8"))
            player.sendLine(f"Strength: {stats[3]}  Dexterity: {stats[4]}  Agility: {stats[5]}".encode("utf-8"))
            player.sendLine(f"Intelligence: {stats[6]}  Wisdom: {stats[7]}".encode("utf-8"))
            player.sendLine(f"Dojo Alignment: {stats[8]}".encode("utf-8"))
        else:
            player.sendLine(b"No stats found for your character.")
    except Exception as e:
        logging.error(f"Error retrieving stats for {player.username}: {e}", exc_info=True)
        player.sendLine(f"Error retrieving stats: {e}".encode('utf-8'))


def handle_loc(player):
    """Display the player's canonical grid location and optional overlay."""
    world_map = UTILITIES.get("WORLD_MAP")
    if not world_map:
        player.sendLine(b"Error: World map is unavailable.")
        return

    location = get_location(world_map, player.x, player.y, WORLD_OVERLAYS)
    player.sendLine(f"Location: ({player.x}, {player.y})".encode("utf-8"))
    if location["overlay"]:
        overlay = location["overlay"]
        player.sendLine(
            f"Area: {overlay['zone_name']}  VNUM: {overlay['vnum']}".encode("utf-8")
        )
    else:
        player.sendLine(f"Terrain: {location['terrain']}".encode("utf-8"))


def handle_who(player, tracked_players=None):
    """Display currently connected characters."""
    online = online_players(players_in_rooms if tracked_players is None else tracked_players)
    player.sendLine(f"Players online: {len(online)}".encode("utf-8"))
    for online_player in online:
        player.sendLine(f"  {online_player.username}".encode("utf-8"))


def handle_survey(player):
    world_map = UTILITIES.get("WORLD_MAP")
    if not world_map:
        player.sendLine(b"Error: World map is unavailable.")
        return
    player.sendLine(
        UTILITIES["render_open_land"](
            player.x,
            player.y,
            world_map=world_map,
            overlays=WORLD_OVERLAYS,
            width_radius=5,
            height_radius=5,
        ).encode("utf-8")
    )

COMMANDS = {
    "look": lambda player, players_in_rooms, raw_args, split_args: handle_look(player, players_in_rooms),
    "score": lambda player, players_in_rooms, raw_args, split_args: handle_score(player, players_in_rooms),
    "status": lambda player, players_in_rooms, raw_args, split_args: handle_score(player, players_in_rooms),
    "loc": lambda player, players_in_rooms, raw_args, split_args: handle_loc(player),
    "who": lambda player, players_in_rooms, raw_args, split_args: handle_who(player, players_in_rooms),
    "survey": lambda player, players_in_rooms, raw_args, split_args: handle_survey(player),
    "north": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "north"),
    "south": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "south"),
    "east": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "east"),
    "west": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "west"),


    
}

