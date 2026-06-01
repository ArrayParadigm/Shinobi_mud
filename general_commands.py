import json
import logging
from command_system import CommandSpec
from locations import LocationPersistenceError, get_location, move_player, online_players
from shinobi_mud import (
    COMMAND_REGISTRY,
    UTILITIES,
    WORLD_OVERLAYS,
    players_in_rooms,
    resolve_command_name,
)

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
        UTILITIES["render_room"](player, WORLD_OVERLAYS)
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
            UTILITIES["render_room"](player, WORLD_OVERLAYS)
            player.list_players_in_room()
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


def handle_help(player, raw_args):
    """Display available commands or detailed help for one command."""
    topic = raw_args.strip().lower()
    if not topic:
        visible_commands = [
            name
            for name, command in COMMAND_REGISTRY.items()
            if command.permission == "player" or player.is_admin
        ]
        player.sendLine(b"Available commands:")
        player.sendLine(", ".join(sorted(visible_commands)).encode("utf-8"))
        player.sendLine(b"Use help <command> for details.")
        return

    command_name, matches = resolve_command_name(topic)
    if not command_name:
        if matches:
            player.sendLine(
                f"Ambiguous help topic '{topic}': {', '.join(matches)}".encode("utf-8")
            )
        else:
            player.sendLine(f"No help found for: {topic}".encode("utf-8"))
        return

    command = COMMAND_REGISTRY[command_name]
    if command.permission == "admin" and not player.is_admin:
        player.sendLine(f"No help found for: {topic}".encode("utf-8"))
        return

    player.sendLine(f"{command.name}: {command.description}".encode("utf-8"))
    player.sendLine(f"Usage: {command.usage}".encode("utf-8"))
    if command.aliases:
        player.sendLine(f"Aliases: {', '.join(command.aliases)}".encode("utf-8"))


COMMANDS = {
    "look": CommandSpec("look", lambda player, rooms, raw, args: handle_look(player, rooms), "look", "Display nearby terrain and players.", max_args=0),
    "score": CommandSpec("score", lambda player, rooms, raw, args: handle_score(player, rooms), "score", "Display your character sheet.", aliases=("status",), max_args=0),
    "loc": CommandSpec("loc", lambda player, rooms, raw, args: handle_loc(player), "loc", "Display your grid coordinates and area.", max_args=0),
    "who": CommandSpec("who", lambda player, rooms, raw, args: handle_who(player, rooms), "who", "List connected characters.", max_args=0),
    "survey": CommandSpec("survey", lambda player, rooms, raw, args: handle_survey(player), "survey", "Display a compact terrain view.", max_args=0),
    "north": CommandSpec("north", lambda player, rooms, raw, args: handle_movement(player, "north"), "north", "Move north.", max_args=0),
    "south": CommandSpec("south", lambda player, rooms, raw, args: handle_movement(player, "south"), "south", "Move south.", max_args=0),
    "east": CommandSpec("east", lambda player, rooms, raw, args: handle_movement(player, "east"), "east", "Move east.", max_args=0),
    "west": CommandSpec("west", lambda player, rooms, raw, args: handle_movement(player, "west"), "west", "Move west.", max_args=0),
    "help": CommandSpec("help", lambda player, rooms, raw, args: handle_help(player, raw), "help [command]", "List commands or explain one command.", max_args=1),
}

