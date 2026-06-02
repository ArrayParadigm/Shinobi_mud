import json
import logging
from body import body_state, body_warnings, chakra_recovery_amount, rest_character
from command_system import CommandSpec
from items import (
    drop_item,
    examine_item,
    format_inventory,
    inventory_items,
    pickup_item,
    remove_item,
    consume_item,
    wield_item,
)
from locations import (
    LocationPersistenceError,
    broadcast_at,
    coordinate_key,
    get_location,
    move_player,
    online_players,
)
from npcs import attack_npc, consider_npc, talk_to_npc, throw_item_at_npc
from techniques import activate_jutsu, jutsu_detail, list_jutsus, list_skills, proficiency_label, skill_detail
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
            color_enabled=getattr(player, "color_enabled", False),
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
                color_enabled=getattr(player, "color_enabled", False),
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
            color_enabled=getattr(player, "color_enabled", False),
        ).encode("utf-8")
    )


def handle_color(player, setting):
    """Toggle ANSI terminal colors for the current connection."""
    requested = setting.strip().lower()
    if requested not in {"on", "off"}:
        player.sendLine(b"Usage: color <on|off>")
        return
    player.color_enabled = requested == "on"
    player.sendLine(f"Color is now {requested}.".encode("utf-8"))


def handle_body(player):
    """Display abstract body resources and current recovery readiness."""
    try:
        state = body_state(player.cursor, player.username)
        if not state:
            player.sendLine(b"Your body state is unavailable right now.")
            return
        player.sendLine(b"Body")
        player.sendLine(
            f"Nutrition: {state['nutrition']}/100  Hydration: {state['hydration']}/100  Fatigue: {state['fatigue']}/100".encode("utf-8")
        )
        player.sendLine(f"Recovery: {state['recovery_state']}".encode("utf-8"))
        player.sendLine(
            f"Short-rest chakra recovery: {chakra_recovery_amount(state)}".encode("utf-8")
        )
        for warning in body_warnings(state):
            player.sendLine(f"Warning: {warning}".encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to display body state for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to display your body state right now.")


def handle_rest(player):
    """Take one deliberate short rest to recover stamina and chakra."""
    try:
        result = rest_character(player.cursor, player.username)
        if not result:
            player.sendLine(b"Your body state is unavailable right now.")
            return
        if result["status"] == "blocked":
            player.sendLine(
                f"You cannot rest until you restore your {result['reason']}.".encode("utf-8")
            )
            return
        player.sendLine(
            (
                f"You rest and recover {result['stamina_restored']} stamina and "
                f"{result['chakra_restored']} chakra."
            ).encode("utf-8")
        )
        player.sendLine(
            (
                f"Stamina: {result['stamina']}/{result['max_stamina']}  "
                f"Chakra: {result['chakra']}/{result['max_chakra']}  "
                f"Fatigue: {result['fatigue']}/100"
            ).encode("utf-8")
        )
    except Exception as exc:
        logging.error("Unable to rest character %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to rest right now.")


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


def handle_consume(player, item_name, expected_type, resource_name, verb):
    """Consume one carried food or drink item."""
    try:
        result = consume_item(
            player.cursor,
            player.username,
            item_name.strip(),
            expected_type,
            resource_name,
        )
        if result["status"] == "missing":
            player.sendLine(b"You are not carrying that item.")
        elif result["status"] == "wrong_type":
            player.sendLine(f'You cannot {verb} {result["name"]}.'.encode("utf-8"))
        elif result["status"] == "full":
            player.sendLine(f"Your {resource_name} is already full.".encode("utf-8"))
        elif result["status"] == "missing_player":
            player.sendLine(b"Your body state is unavailable right now.")
        else:
            player.sendLine(
                (
                    f'You {verb} {result["name"]} and restore '
                    f'{result["restored"]} {resource_name}.'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to %s item for %s: %s", verb, player.username, exc, exc_info=True)
        player.sendLine(f"Unable to {verb} that item right now.".encode("utf-8"))


def handle_progression(player, target, kind, allow_all=False):
    """List or inspect usage-based ordinary skill or jutsu progress."""
    try:
        show_all = allow_all and target.strip().casefold() == "all"
        if kind == "skill":
            rows = list_skills(player.cursor, player.username, include_unavailable=show_all)
            detail = skill_detail
            heading = "All Skills" if show_all else "Skills"
        else:
            rows = list_jutsus(player.cursor, player.username, include_unavailable=show_all)
            detail = jutsu_detail
            heading = "All Jutsus" if show_all else "Jutsus"

        if not target.strip() or show_all:
            player.sendLine(heading.encode("utf-8"))
            if not rows:
                player.sendLine(b"  None")
                return
            for row in rows:
                player.sendLine(
                    (
                        f"  {row['name']}: {proficiency_label(row['progress_percent'])} "
                        f"({row['progress_percent']}%)"
                        f"{' [unimplemented]' if not row['is_available'] else ''}"
                    ).encode("utf-8")
                )
            return

        result = detail(player.cursor, player.username, target)
        if not result:
            player.sendLine(f"You do not know that {kind}.".encode("utf-8"))
        else:
            player.sendLine(result["name"].encode("utf-8"))
            player.sendLine(result["description"].encode("utf-8"))
            player.sendLine(
                f'Proficiency: {result["proficiency"]} ({result["progress_percent"]}%)'.encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to display %s progress for %s: %s", kind, player.username, exc, exc_info=True)
        player.sendLine(b"Unable to display your technique progress right now.")


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


def handle_consider(player, npc_name):
    """Display one visible NPC's authored combat details."""
    try:
        npc = consider_npc(player.cursor, player.x, player.y, npc_name.strip())
        if not npc:
            player.sendLine(b"You do not see that character here.")
            return
        player.sendLine(npc["name"].encode("utf-8"))
        player.sendLine(npc["description"].encode("utf-8"))
        player.sendLine(f'Health: {npc["health"]}/{npc["max_health"]}'.encode("utf-8"))
        if npc["behavior"] != "hostile":
            player.sendLine(b"This character is not a combat target.")
            return
        player.sendLine(
            (
                f'Attack: {npc["attack_damage"]}  '
                f'Accuracy: {npc["accuracy"]}  Evasion: {npc["evasion"]}'
            ).encode("utf-8")
        )
    except Exception as exc:
        logging.error("Unable to consider NPC for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to inspect that character right now.")


def _broadcast_combat(player, message):
    broadcast_at(
        players_in_rooms,
        coordinate_key(player.x, player.y),
        message,
        exclude=player,
    )


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
            message = (
                f'You strike {result["npc_name"]} for {result["player_damage"]} '
                "damage and defeat it."
            )
            player.sendLine(message.encode("utf-8"))
            _broadcast_combat(
                player,
                (
                    f'{player.username} strikes {result["npc_name"]} for '
                    f'{result["player_damage"]} damage and defeats it.'
                ),
            )
            return

        if result["player_hit"]:
            player.sendLine(
                (
                f'You strike {result["npc_name"]} for {result["player_damage"]} damage. '
                f'{result["npc_name"]} has {result["npc_health"]} health remaining.'
                ).encode("utf-8")
            )
            _broadcast_combat(
                player,
                (
                    f'{player.username} strikes {result["npc_name"]} for '
                    f'{result["player_damage"]} damage. '
                    f'{result["npc_name"]} has {result["npc_health"]} health remaining.'
                ),
            )
        else:
            player.sendLine(f'You attack {result["npc_name"]}, but miss.'.encode("utf-8"))
            _broadcast_combat(
                player,
                f'{player.username} attacks {result["npc_name"]}, but misses.',
            )

        if result["substitution"]:
            player.sendLine(
                (
                    f'You evade {result["npc_name"]} through Substitution Technique. '
                    f'Jutsu: {result["substitution"]["proficiency"]} '
                    f'({result["substitution"]["progress_percent"]}%).'
                ).encode("utf-8")
            )
            _broadcast_combat(
                player,
                f'{player.username} evades {result["npc_name"]} through Substitution Technique.',
            )
        elif not result["npc_hit"]:
            player.sendLine(f'{result["npc_name"]} attacks you, but misses.'.encode("utf-8"))
            _broadcast_combat(
                player,
                f'{result["npc_name"]} attacks {player.username}, but misses.',
            )
        elif result["player_defeated"]:
            player.sendLine(
                (
                    f'{result["npc_name"]} strikes you for {result["npc_damage"]} damage. '
                    f'You are defeated, then recover here with {result["player_health"]} health.'
                ).encode("utf-8")
            )
            _broadcast_combat(
                player,
                (
                    f'{result["npc_name"]} strikes {player.username} for '
                    f'{result["npc_damage"]} damage. '
                    f'{player.username} is defeated and recovers here.'
                ),
            )
        else:
            player.sendLine(
                (
                    f'{result["npc_name"]} strikes you for {result["npc_damage"]} damage. '
                    f'You have {result["player_health"]} health remaining.'
                ).encode("utf-8")
            )
            _broadcast_combat(
                player,
                (
                    f'{result["npc_name"]} strikes {player.username} for '
                    f'{result["npc_damage"]} damage. '
                    f'{player.username} has {result["player_health"]} health remaining.'
                ),
            )
    except Exception as exc:
        logging.error("Unable to attack NPC for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to attack that character right now.")


def handle_usejutsu(player, target):
    """Activate one implemented jutsu by name or unique prefix."""
    try:
        result = activate_jutsu(player.cursor, player.username, target)
        if result["status"] == "missing":
            player.sendLine(b"You do not know that jutsu.")
        elif result["status"] == "unimplemented":
            player.sendLine(f'{result["name"]} is not implemented yet.'.encode("utf-8"))
        elif result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
        elif result["status"] == "insufficient_chakra":
            player.sendLine(f'You do not have enough chakra to activate {result["name"]}.'.encode("utf-8"))
        elif result["status"] == "active":
            player.sendLine(f'{result["name"]} is already active.'.encode("utf-8"))
        elif result["status"] == "cooldown":
            player.sendLine(f'{result["name"]} is still on cooldown.'.encode("utf-8"))
        else:
            player.sendLine(
                (
                    f'You prepare {result["name"]} for {result["active_seconds"]} seconds. '
                    f'Chakra: {result["chakra"]}.'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to activate jutsu for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to activate that jutsu right now.")


def handle_throw(player, raw_args):
    """Throw one carried authored item at a nearby hostile NPC."""
    separator_index = raw_args.casefold().find(" at ")
    if separator_index < 0:
        player.sendLine(b"Usage: throw <item> at <character>")
        return
    item_name = raw_args[:separator_index]
    npc_name = raw_args[separator_index + 4:]
    try:
        result = throw_item_at_npc(
            player.cursor,
            player.username,
            player.x,
            player.y,
            item_name.strip(),
            npc_name.strip(),
        )
        if result["status"] == "missing_item":
            player.sendLine(b"You are not carrying that item.")
        elif result["status"] == "not_throwable":
            player.sendLine(f'{result["item_name"]} is not throwable.'.encode("utf-8"))
        elif result["status"] == "missing_target":
            player.sendLine(b"You do not see that character within throwing range.")
        elif result["status"] == "not_attackable":
            player.sendLine(f'{result["npc_name"]} is not a combat target.'.encode("utf-8"))
        elif result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
        elif result["status"] == "npc_defeated":
            player.sendLine(
                (
                    f'You throw {result["item_name"]} at {result["npc_name"]} for '
                    f'{result["player_damage"]} damage and defeat it. '
                    f'Throw: {result["proficiency"]} ({result["progress_percent"]}%).'
                ).encode("utf-8")
            )
        elif result["player_hit"]:
            player.sendLine(
                (
                    f'You throw {result["item_name"]} at {result["npc_name"]} for '
                    f'{result["player_damage"]} damage. '
                    f'{result["npc_name"]} has {result["npc_health"]} health remaining. '
                    f'Throw: {result["proficiency"]} ({result["progress_percent"]}%).'
                ).encode("utf-8")
            )
        else:
            player.sendLine(
                (
                    f'You throw {result["item_name"]} at {result["npc_name"]}, but miss. '
                    f'Throw: {result["proficiency"]} ({result["progress_percent"]}%).'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to throw item for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to throw that item right now.")


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
    "color": CommandSpec("color", lambda player, rooms, raw, args: handle_color(player, raw), "color <on|off>", "Toggle ANSI terminal colors for this connection.", min_args=1, max_args=1),
    "body": CommandSpec("body", lambda player, rooms, raw, args: handle_body(player), "body", "Display your body resources and recovery readiness.", max_args=0),
    "rest": CommandSpec("rest", lambda player, rooms, raw, args: handle_rest(player), "rest", "Recover stamina and chakra through a short rest.", max_args=0),
    "inventory": CommandSpec("inventory", lambda player, rooms, raw, args: handle_inventory(player), "inventory", "List the items you carry.", aliases=("inv",), max_args=0),
    "get": CommandSpec("get", lambda player, rooms, raw, args: handle_get(player, raw), "get <item>", "Pick up an item at your location.", min_args=1),
    "drop": CommandSpec("drop", lambda player, rooms, raw, args: handle_drop(player, raw), "drop <item>", "Drop a carried item at your location.", min_args=1),
    "examine": CommandSpec("examine", lambda player, rooms, raw, args: handle_examine(player, raw), "examine <item>", "Inspect a visible or carried item.", min_args=1),
    "wield": CommandSpec("wield", lambda player, rooms, raw, args: handle_wield(player, raw), "wield <item>", "Equip a carried item.", min_args=1),
    "remove": CommandSpec("remove", lambda player, rooms, raw, args: handle_remove(player, raw), "remove <item>", "Unequip a carried item.", min_args=1),
    "eat": CommandSpec("eat", lambda player, rooms, raw, args: handle_consume(player, raw, "food", "nutrition", "eat"), "eat <item>", "Eat a carried food item to restore nutrition.", min_args=1),
    "drink": CommandSpec("drink", lambda player, rooms, raw, args: handle_consume(player, raw, "drink", "hydration", "drink"), "drink <item>", "Drink a carried beverage to restore hydration.", min_args=1),
    "prac": CommandSpec("prac", lambda player, rooms, raw, args: handle_progression(player, raw, "skill"), "prac [skill]", "List skills or inspect usage-based proficiency.", max_args=2),
    "train": CommandSpec("train", lambda player, rooms, raw, args: handle_progression(player, raw, "jutsu"), "train [jutsu]", "List jutsus or inspect usage-based proficiency.", max_args=3),
    "skill": CommandSpec("skill", lambda player, rooms, raw, args: handle_progression(player, raw, "skill", allow_all=True), "skill [all|skill]", "List available skills, inspect one, or show the full catalog.", max_args=2),
    "jutsu": CommandSpec("jutsu", lambda player, rooms, raw, args: handle_progression(player, raw, "jutsu", allow_all=True), "jutsu [all|jutsu]", "List available jutsus, inspect one, or show the full catalog.", max_args=3),
    "usejutsu": CommandSpec("usejutsu", lambda player, rooms, raw, args: handle_usejutsu(player, raw), "usejutsu <jutsu>", "Activate an implemented jutsu.", min_args=1, max_args=3),
    "talk": CommandSpec("talk", lambda player, rooms, raw, args: handle_talk(player, raw), "talk <character>", "Talk to a character at your location.", min_args=1),
    "consider": CommandSpec("consider", lambda player, rooms, raw, args: handle_consider(player, raw), "consider <character>", "Inspect a character's combat details.", min_args=1),
    "attack": CommandSpec("attack", lambda player, rooms, raw, args: handle_attack(player, raw), "attack <character>", "Strike a hostile character at your location.", min_args=1),
    "throw": CommandSpec("throw", lambda player, rooms, raw, args: handle_throw(player, raw), "throw <item> at <character>", "Throw a carried ranged item at a nearby hostile character.", min_args=3, args_validator=lambda args: "at" in [arg.lower() for arg in args]),
    "north": CommandSpec("north", lambda player, rooms, raw, args: handle_movement(player, "north"), "north", "Move north.", max_args=0),
    "south": CommandSpec("south", lambda player, rooms, raw, args: handle_movement(player, "south"), "south", "Move south.", max_args=0),
    "east": CommandSpec("east", lambda player, rooms, raw, args: handle_movement(player, "east"), "east", "Move east.", max_args=0),
    "west": CommandSpec("west", lambda player, rooms, raw, args: handle_movement(player, "west"), "west", "Move west.", max_args=0),
    "help": CommandSpec("help", lambda player, rooms, raw, args: handle_help(player, raw), "help [command]", "List commands or explain one command.", max_args=1),
}

