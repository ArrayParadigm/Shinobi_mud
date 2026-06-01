import json
import logging
from command_system import CommandSpec
from items import (
    drop_item,
    examine_item,
    format_inventory,
    inventory_items,
    pickup_item,
    remove_item,
    wield_item,
)
from locations import LocationPersistenceError, get_location, move_player, online_players
from npcs import attack_npc, talk_to_npc
from shinobi_mud import (
    COMMAND_REGISTRY,
    UTILITIES,
    WORLD_OVERLAYS,
    players_in_rooms,
    resolve_command_name,
)

logging.info("general_commands imported")


def handle_look(player, players_in_rooms=None, raw_args=""):
    """Display the current location or inspect one visible item."""
    if raw_args:
        if raw_args.lower().startswith("at "):
            handle_examine(player, raw_args[3:])
        else:
            player.sendLine(b"Usage: look [at <item>]")
        return

    WORLD_MAP = UTILITIES.get("WORLD_MAP")
    if not WORLD_MAP:
        player.sendLine(b"Error: World map is not available.")
        return

    try:
        render_open_land = UTILITIES["render_open_land"]
        UTILITIES["render_room"](player, WORLD_OVERLAYS)
        map_view = render_open_land(
            player.x,
            player.y,
            world_map=WORLD_MAP,
            overlays=WORLD_OVERLAYS,
            width_radius=5,
            height_radius=2,
        )
        player.sendLine(map_view.encode("utf-8"))
        player.list_players_in_room()
        player.list_nearby_players()
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
            UTILITIES["render_room"](player, WORLD_OVERLAYS)
            map_view = UTILITIES["render_open_land"](
                player.x,
                player.y,
                world_map=world_map,
                overlays=WORLD_OVERLAYS,
                width_radius=5,
                height_radius=2,
            )
            player.sendLine(map_view.encode("utf-8"))
            player.list_players_in_room()
            player.list_nearby_players()
        else:
            player.sendLine(b"You can't go that way.")
    except LocationPersistenceError:
        logging.warning("Movement save blocked for player %s.", player.username)
        player.sendLine(b"Movement could not be saved. Please try again.")

def handle_score(player, players_in_rooms=None):
    """Display the player's current character sheet."""
    try:
        player.cursor.execute(
            "SELECT health, max_health, stamina, max_stamina, chakra, max_chakra, "
            "strength, dexterity, agility, intelligence, wisdom, dojo_alignment, "
            "role_type, clan, natural_release "
            "FROM players WHERE username=?",
            (player.username,)
        )
        stats = player.cursor.fetchone()
        if stats:
            player.sendLine(f"Score for {player.username}".encode("utf-8"))
            player.sendLine(b"--------------------")
            player.sendLine(f"Health: {stats[0]}/{stats[1]}  Stamina: {stats[2]}/{stats[3]}  Chakra: {stats[4]}/{stats[5]}".encode("utf-8"))
            player.sendLine(f"Strength: {stats[6]}  Dexterity: {stats[7]}  Agility: {stats[8]}".encode("utf-8"))
            player.sendLine(f"Intelligence: {stats[9]}  Wisdom: {stats[10]}".encode("utf-8"))
            player.sendLine(f"Specialty: {stats[12]}  Clan: {stats[13]}  Release: {stats[14]}".encode("utf-8"))
            player.sendLine(f"Dojo Alignment: {stats[11]}".encode("utf-8"))
            player.sendLine(f"Location: ({player.x}, {player.y})".encode("utf-8"))
            overlay = WORLD_OVERLAYS.get((player.x, player.y))
            if overlay:
                player.sendLine(
                    f"Area: {overlay['zone_name']}  VNUM: {overlay['vnum']}".encode("utf-8")
                )
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
            width_radius=20,
            height_radius=10,
        ).encode("utf-8")
    )


def handle_inventory(player):
    """List persistent items carried by the player."""
    try:
        items = inventory_items(player.cursor, player.username)
        player.sendLine(b"Inventory")
        for line in format_inventory(items):
            player.sendLine(line.encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to list inventory for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to list your inventory right now.")


def handle_get(player, item_name):
    """Pick up one named item from the current grid coordinate."""
    try:
        picked_up = pickup_item(
            player.cursor,
            player.username,
            player.x,
            player.y,
            item_name.strip(),
        )
        if picked_up:
            player.sendLine(f"You pick up {picked_up}.".encode("utf-8"))
        else:
            player.sendLine(b"You do not see that item here.")
    except Exception as exc:
        logging.error("Unable to pick up item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to pick up that item right now.")


def handle_drop(player, item_name):
    """Drop one named inventory item at the current grid coordinate."""
    try:
        dropped = drop_item(
            player.cursor,
            player.username,
            player.x,
            player.y,
            item_name.strip(),
        )
        if dropped:
            player.sendLine(f"You drop {dropped}.".encode("utf-8"))
        else:
            player.sendLine(b"You are not carrying that item.")
    except Exception as exc:
        logging.error("Unable to drop item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to drop that item right now.")


def handle_examine(player, item_name):
    """Inspect one visible or carried item by name, keyword, or prefix."""
    try:
        item = examine_item(
            player.cursor,
            player.username,
            player.x,
            player.y,
            item_name.strip(),
        )
        if not item:
            player.sendLine(b"You do not see or carry that item.")
            return
        player.sendLine(item["name"].encode("utf-8"))
        player.sendLine(item["description"].encode("utf-8"))
        player.sendLine(f"Type: {item['item_type']}".encode("utf-8"))
        if item["use_text"]:
            player.sendLine(f"Use: {item['use_text']}".encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to examine item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to examine that item right now.")


def handle_wield(player, item_name):
    """Equip one carried item in its authored slot."""
    try:
        result = wield_item(player.cursor, player.username, item_name.strip())
        if result["status"] == "missing":
            player.sendLine(b"You are not carrying that item.")
        elif result["status"] == "not_equippable":
            player.sendLine(f'{result["name"]} cannot be equipped.'.encode("utf-8"))
        else:
            player.sendLine(f'You wield {result["name"]}.'.encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to wield item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to wield that item right now.")


def handle_remove(player, item_name):
    """Unequip one carried item."""
    try:
        result = remove_item(player.cursor, player.username, item_name.strip())
        if result["status"] == "missing":
            player.sendLine(b"You are not carrying that item.")
        elif result["status"] == "not_equipped":
            player.sendLine(f'{result["name"]} is not equipped.'.encode("utf-8"))
        else:
            player.sendLine(f'You remove {result["name"]}.'.encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to remove item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to remove that item right now.")


def handle_talk(player, npc_name):
    """Talk to one NPC at the current grid coordinate."""
    try:
        npc = talk_to_npc(player.cursor, player.x, player.y, npc_name.strip())
        if npc:
            player.sendLine(f'{npc["name"]} says, "{npc["dialogue"]}"'.encode("utf-8"))
        else:
            player.sendLine(b"You do not see that character here.")
    except Exception as exc:
        logging.error("Unable to talk to NPC for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to talk to that character right now.")


def handle_attack(player, npc_name):
    """Resolve one turn of melee combat against an NPC."""
    try:
        result = attack_npc(
            player.cursor,
            player.username,
            player.x,
            player.y,
            npc_name.strip(),
        )
        if result["status"] == "missing_target":
            player.sendLine(b"You do not see that character here.")
            return
        if result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
            return
        if result["status"] == "not_attackable":
            player.sendLine(f'{result["npc_name"]} is not a combat target.'.encode("utf-8"))
            return
        if result["status"] == "npc_defeated":
            player.sendLine(
                (
                    f'You strike {result["npc_name"]} for {result["player_damage"]} '
                    "damage and defeat it."
                ).encode("utf-8")
            )
            return

        player.sendLine(
            (
                f'You strike {result["npc_name"]} for {result["player_damage"]} damage. '
                f'{result["npc_name"]} has {result["npc_health"]} health remaining.'
            ).encode("utf-8")
        )
        if result["player_defeated"]:
            player.sendLine(
                (
                    f'{result["npc_name"]} strikes you for {result["npc_damage"]} damage. '
                    f'You are defeated, then recover with {result["player_health"]} health.'
                ).encode("utf-8")
            )
        else:
            player.sendLine(
                (
                    f'{result["npc_name"]} strikes you for {result["npc_damage"]} damage. '
                    f'You have {result["player_health"]} health remaining.'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to attack NPC for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to attack that character right now.")


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
    "look": CommandSpec("look", lambda player, rooms, raw, args: handle_look(player, rooms, raw), "look [at <item>]", "Display your location or inspect an item.", args_validator=lambda args: not args or (len(args) >= 2 and args[0].lower() == "at")),
    "score": CommandSpec("score", lambda player, rooms, raw, args: handle_score(player, rooms), "score", "Display your character sheet.", aliases=("status",), max_args=0),
    "loc": CommandSpec("loc", lambda player, rooms, raw, args: handle_loc(player), "loc", "Display your grid coordinates and area.", max_args=0),
    "who": CommandSpec("who", lambda player, rooms, raw, args: handle_who(player, rooms), "who", "List connected characters.", max_args=0),
    "survey": CommandSpec("survey", lambda player, rooms, raw, args: handle_survey(player), "survey", "Display a compact terrain view.", max_args=0),
    "inventory": CommandSpec("inventory", lambda player, rooms, raw, args: handle_inventory(player), "inventory", "List the items you carry.", aliases=("inv",), max_args=0),
    "get": CommandSpec("get", lambda player, rooms, raw, args: handle_get(player, raw), "get <item>", "Pick up an item at your location.", min_args=1),
    "drop": CommandSpec("drop", lambda player, rooms, raw, args: handle_drop(player, raw), "drop <item>", "Drop a carried item at your location.", min_args=1),
    "examine": CommandSpec("examine", lambda player, rooms, raw, args: handle_examine(player, raw), "examine <item>", "Inspect a visible or carried item.", min_args=1),
    "wield": CommandSpec("wield", lambda player, rooms, raw, args: handle_wield(player, raw), "wield <item>", "Equip a carried item.", min_args=1),
    "remove": CommandSpec("remove", lambda player, rooms, raw, args: handle_remove(player, raw), "remove <item>", "Unequip a carried item.", min_args=1),
    "talk": CommandSpec("talk", lambda player, rooms, raw, args: handle_talk(player, raw), "talk <character>", "Talk to a character at your location.", min_args=1),
    "attack": CommandSpec("attack", lambda player, rooms, raw, args: handle_attack(player, raw), "attack <character>", "Strike a hostile character at your location.", min_args=1),
    "north": CommandSpec("north", lambda player, rooms, raw, args: handle_movement(player, "north"), "north", "Move north.", max_args=0),
    "south": CommandSpec("south", lambda player, rooms, raw, args: handle_movement(player, "south"), "south", "Move south.", max_args=0),
    "east": CommandSpec("east", lambda player, rooms, raw, args: handle_movement(player, "east"), "east", "Move east.", max_args=0),
    "west": CommandSpec("west", lambda player, rooms, raw, args: handle_movement(player, "west"), "west", "Move west.", max_args=0),
    "help": CommandSpec("help", lambda player, rooms, raw, args: handle_help(player, raw), "help [command]", "List commands or explain one command.", max_args=1),
}

