import json
import logging
import presentation
from body import apply_vacuum_exposure, body_state, body_warnings, chakra_recovery_amount, rest_character
from combat import (
    combat_status,
    engage_npc,
    list_combat_techniques,
    list_stances,
    queue_combat_technique,
    set_stance,
)
from command_system import CommandSpec
from feedback import DEFAULT_BUGS_FILE, DEFAULT_SUGGESTIONS_FILE, append_feedback
from help_content import (
    DEFAULT_CATEGORY_FILE,
    DEFAULT_HELP_FILE,
    command_help,
    load_command_categories,
    load_help_catalog,
)
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
from npcs import consider_npc, npc_locations, talk_to_npc, throw_item_at_npc
from techniques import (
    activate_jutsu,
    jutsu_detail,
    list_jutsus,
    list_skills,
    practice_skill,
    proficiency_label,
    skill_detail,
    train_jutsu,
)
from shinobi_mud import (
    ACTIVE_CONFIG,
    COMMAND_REGISTRY,
    UTILITIES,
    WORLD_OVERLAYS,
    players_in_rooms,
    resolve_command_name,
)

logging.info("general_commands imported")

NORMAL_MAP_WIDTH_RADIUS = 5
NORMAL_MAP_HEIGHT_RADIUS = 5
SURVEY_MAP_WIDTH_RADIUS = 16
SURVEY_MAP_HEIGHT_RADIUS = 8


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
        flags = _current_room_flags(player)
        render_open_land = UTILITIES["render_open_land"]
        UTILITIES["render_room"](player, WORLD_OVERLAYS)
        if "darkness" in flags:
            player.sendLine(b"It is too dark to read the nearby map.")
            return
        map_view = render_open_land(
            player.x,
            player.y,
            world_map=WORLD_MAP,
            overlays=WORLD_OVERLAYS,
            width_radius=2 if "indoor" in flags else NORMAL_MAP_WIDTH_RADIUS,
            height_radius=2 if "indoor" in flags else NORMAL_MAP_HEIGHT_RADIUS,
            color_enabled=getattr(player, "color_enabled", False),
            bright_mode="brightness" in flags,
            player_locations=_other_player_locations(player, NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
            npc_locations=_npc_locations(player, NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
        )
        player.sendLine(map_view.encode("utf-8"))
        player.sendLine(presentation.divider("Nearby", getattr(player, "color_enabled", False)).encode("utf-8"))
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
            flags = _current_room_flags(player)
            if "vacuum" in flags:
                vacuum = apply_vacuum_exposure(player.cursor, player.username)
                if vacuum:
                    player.sendLine(
                        f"Vacuum strains your body. Fatigue: {vacuum['fatigue']}/100  Health: {vacuum['health']}/{vacuum['max_health']}".encode("utf-8")
                    )
            map_view = UTILITIES["render_open_land"](
                player.x,
                player.y,
                world_map=world_map,
                overlays=WORLD_OVERLAYS,
                width_radius=2 if "indoor" in flags else NORMAL_MAP_WIDTH_RADIUS,
                height_radius=2 if "indoor" in flags else NORMAL_MAP_HEIGHT_RADIUS,
                color_enabled=getattr(player, "color_enabled", False),
                bright_mode="brightness" in flags,
                player_locations=_other_player_locations(player, NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
                npc_locations=_npc_locations(player, NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
            )
            if "darkness" in flags:
                player.sendLine(b"It is too dark to read the nearby map.")
            else:
                player.sendLine(map_view.encode("utf-8"))
            player.sendLine(presentation.divider("Nearby", getattr(player, "color_enabled", False)).encode("utf-8"))
            player.list_players_in_room()
            player.list_nearby_players()
            status = combat_status(player.cursor, player.username)
            if status and status["npc_name"]:
                range_state = "in range" if status["auto_in_range"] else "out of range"
                player.sendLine(
                    (
                        f'Combat range: {status["distance"]} step(s) from '
                        f'{status["npc_name"]}; basic auto attack {range_state}.'
                    ).encode("utf-8")
                )
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
            "role_type, clan, natural_release, fatigue, description "
            "FROM players WHERE username=?",
            (player.username,)
        )
        stats = player.cursor.fetchone()
        if stats:
            player.sendLine(f"Score for {player.username}".encode("utf-8"))
            player.sendLine(b"--------------------")
            player.sendLine(f"Health: {stats[0]}/{stats[1]}".encode("utf-8"))
            player.sendLine(f"Stamina: {stats[2]}/{stats[3]}".encode("utf-8"))
            player.sendLine(f"Chakra: {stats[4]}/{stats[5]}".encode("utf-8"))
            player.sendLine(f"Fatigue: {_fatigue_label(stats[15])}".encode("utf-8"))
            player.sendLine(
                (
                    f"Strength: {stats[6]}  Intellect: {stats[9]}  "
                    f"Dexterity: {stats[7]}  Agility: {stats[8]}  Condition: {stats[10]}"
                ).encode("utf-8")
            )
            player.sendLine(f"Description: {stats[16]}".encode("utf-8"))
            player.sendLine(f"Specialty: {stats[12]}  Clan: {stats[13]}  Release: {stats[14]}".encode("utf-8"))
            player.sendLine(f"Dojo Alignment: {stats[11]}".encode("utf-8"))
            stance = combat_status(player.cursor, player.username)
            if stance:
                player.sendLine(f"Stance: {stance['stance_name']}".encode("utf-8"))
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


def _fatigue_label(value):
    value = int(value)
    if value >= 90:
        return "depleted"
    if value >= 70:
        return "exhausted"
    if value >= 50:
        return "tired"
    if value >= 25:
        return "ready"
    return "fresh"


def _current_room_flags(player):
    overlay = WORLD_OVERLAYS.get((player.x, player.y))
    if not overlay:
        return {"outdoor"}
    return set(overlay["room"].get("flags", []) or ["outdoor"])


def _other_player_locations(player, width_radius, height_radius):
    locations = set()
    for other_player in online_players(players_in_rooms):
        if other_player is player:
            continue
        if abs(other_player.x - player.x) <= width_radius and abs(other_player.y - player.y) <= height_radius:
            locations.add((other_player.x, other_player.y))
    return locations


def _npc_locations(player, width_radius, height_radius):
    try:
        return npc_locations(player.cursor, player.x, player.y, width_radius, height_radius)
    except Exception as exc:
        logging.warning("Unable to gather NPC map markers for %s: %s", player.username, exc)
        return []


def handle_description(player, raw_args):
    """View or edit the character's public description."""
    text = raw_args.strip()
    if not text:
        row = player.cursor.execute(
            "SELECT description FROM players WHERE username=?",
            (player.username,),
        ).fetchone()
        player.sendLine(f"Description: {row['description']}".encode("utf-8"))
        return
    player.cursor.execute(
        "UPDATE players SET description=? WHERE username=?",
        (presentation.sanitize_player_text(text), player.username),
    )
    player.cursor.connection.commit()
    player.sendLine(b"Description updated.")


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
    flags = _current_room_flags(player)
    if "darkness" in flags:
        player.sendLine(b"It is too dark to survey the area.")
        return
    player.sendLine(
        UTILITIES["render_open_land"](
            player.x,
            player.y,
            world_map=world_map,
            overlays=WORLD_OVERLAYS,
            width_radius=2 if "indoor" in flags else SURVEY_MAP_WIDTH_RADIUS,
            height_radius=2 if "indoor" in flags else SURVEY_MAP_HEIGHT_RADIUS,
            color_enabled=getattr(player, "color_enabled", False),
            bright_mode="brightness" in flags,
            player_locations=_other_player_locations(player, SURVEY_MAP_WIDTH_RADIUS, SURVEY_MAP_HEIGHT_RADIUS),
            npc_locations=_npc_locations(player, SURVEY_MAP_WIDTH_RADIUS, SURVEY_MAP_HEIGHT_RADIUS),
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


def handle_feedback(player, raw_args, file_config_key, default_file, command_name, label, confirmation):
    """Capture one player-authored suggestion or bug report."""
    message = raw_args.strip()
    if not message:
        player.sendLine(f"Usage: {command_name} <message>".encode("utf-8"))
        return
    try:
        line = append_feedback(
            player.username,
            message,
            ACTIVE_CONFIG.get(file_config_key, default_file),
            label,
        )
        if not line:
            player.sendLine(f"Usage: {command_name} <message>".encode("utf-8"))
            return
        logging.info("Player %s submitted %s feedback.", player.username, label.lower())
        player.sendLine(confirmation.encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to record %s feedback for %s: %s", label, player.username, exc, exc_info=True)
        player.sendLine(b"Unable to record that right now.")


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
        flags = _current_room_flags(player)
        result = rest_character(
            player.cursor,
            player.username,
            recovery_bonus=2 if "recovery-friendly" in flags else 0,
        )
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
        if "recovery-friendly" in flags:
            player.sendLine(b"This room supports recovery.")
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
        if isinstance(picked_up, dict) and picked_up.get("status") == "not_takeable":
            player.sendLine(f"You cannot pick up {picked_up['name']}.".encode("utf-8"))
        elif isinstance(picked_up, dict) and picked_up.get("status") == "taken":
            player.sendLine(f"You pick up {picked_up['name']}.".encode("utf-8"))
        elif picked_up:
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
                        f"  {row['name']}: {proficiency_label(row['progress_points'])} "
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


def handle_practice(player, target, kind):
    """Advance one skill or jutsu through deliberate practice."""
    if not target.strip():
        handle_progression(player, "", kind)
        return
    try:
        if kind == "skill":
            result = practice_skill(player.cursor, player.username, target)
            verb = "practice"
        else:
            result = train_jutsu(player.cursor, player.username, target)
            verb = "train"
        if result["status"] == "missing":
            player.sendLine(f"You do not know that {kind}.".encode("utf-8"))
            return
        if result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
            return
        player.sendLine(f"You {verb} {result['name']}.".encode("utf-8"))
        for milestone in result["milestones"]:
            if milestone == "tier":
                player.sendLine(f"You feel more comfortable performing {result['name']}.".encode("utf-8"))
            elif milestone == "ten_percent":
                player.sendLine(f"You feel more confident performing {result['name']}.".encode("utf-8"))
        player.sendLine(
            f"{result['name']}: {result['proficiency']}".encode("utf-8")
        )
    except Exception as exc:
        logging.error("Unable to practice %s for %s: %s", kind, player.username, exc, exc_info=True)
        player.sendLine(b"Unable to practice right now.")


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
    """Enter or retarget slow pulse combat against a hostile NPC."""
    try:
        if _current_room_flags(player) & {"safe", "no-combat"}:
            player.sendLine(b"Combat is not allowed here.")
            return
        result = engage_npc(
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
        player.sendLine(
            (
                f'You engage {result["npc_name"]}. Basic auto attacks pulse every '
                f'{result["pulse_seconds"]} seconds while you are in range.'
            ).encode("utf-8")
        )
    except Exception as exc:
        logging.error("Unable to attack NPC for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to attack that character right now.")


def handle_combat(player):
    """Display the current stance, engagement target, and auto-attack range."""
    try:
        status = combat_status(player.cursor, player.username)
        if not status:
            player.sendLine(b"Your character is unavailable right now.")
            return
        player.sendLine(b"Combat")
        player.sendLine(
            (
                f'Stance: {status["stance_name"]}  Pulse: {status["pulse_seconds"]}s  '
                f'Accuracy: {status["accuracy_bonus"]:+d}  '
                f'Evasion: {status["evasion_bonus"]:+d}  Damage: {status["damage_bonus"]:+d}  '
                f'Damage reduction: {status["damage_reduction_bonus"]:+d}'
            ).encode("utf-8")
        )
        if not status["npc_name"]:
            player.sendLine(b"Engagement: none")
            return
        range_state = "in range" if status["auto_in_range"] else "out of range"
        player.sendLine(
            (
                f'Engagement: {status["npc_name"]} '
                f'({status["npc_health"]}/{status["npc_max_health"]} health), '
                f'{status["distance"]} step(s) away; basic auto attack {range_state}.'
            ).encode("utf-8")
        )
        if status["action_key"]:
            player.sendLine(f'Queued modifier: {status["action_key"]}'.encode("utf-8"))
    except Exception as exc:
        logging.error("Unable to display combat state for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to display combat state right now.")


def handle_stance(player, target):
    """List authored stances or switch the character's persistent stance."""
    try:
        if not target.strip():
            player.sendLine(b"Stances")
            for stance in list_stances(player.cursor):
                player.sendLine(
                    (
                        f'  {stance["name"]}: {stance["accuracy_bonus"]:+d} accuracy, '
                        f'{stance["evasion_bonus"]:+d} evasion, '
                        f'{stance["damage_bonus"]:+d} damage, '
                        f'{stance["damage_reduction_bonus"]:+d} damage reduction'
                    ).encode("utf-8")
                )
            return
        result = set_stance(player.cursor, player.username, target)
        if result["status"] == "missing":
            player.sendLine(b"You do not know that stance.")
        elif result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
        else:
            player.sendLine(
                (
                    f'You settle into {result["name"]}. '
                    f'Accuracy {result["accuracy_bonus"]:+d}, evasion {result["evasion_bonus"]:+d}, '
                    f'damage {result["damage_bonus"]:+d}, '
                    f'damage reduction {result["damage_reduction_bonus"]:+d}.'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to set stance for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to change stance right now.")


def _technique_effect_summary(technique):
    effects = []
    if technique["damage_bonus"]:
        effects.append(f'damage {technique["damage_bonus"]:+d}')
    if technique["accuracy_bonus"]:
        effects.append(f'accuracy {technique["accuracy_bonus"]:+d}')
    if technique["evasion_bonus"]:
        effects.append(f'evasion {technique["evasion_bonus"]:+d}')
    if technique["damage_reduction_bonus"]:
        effects.append(f'damage reduction {technique["damage_reduction_bonus"]:+d}')
    if technique["max_range"]:
        effects.append(f'range {technique["max_range"]}')
    if technique["skip_attack"]:
        effects.append("skip attack")
    if technique["stamina_restore"]:
        effects.append(f'restore {technique["stamina_restore"]} stamina')
    return ", ".join(effects) if effects else "no pulse modifier"


def handle_technique(player, target):
    """List or queue one stamina-based fighting technique."""
    try:
        if not target.strip():
            player.sendLine(b"Techniques")
            rows = list_combat_techniques(player.cursor)
            if not rows:
                player.sendLine(b"  none")
                return
            for technique in rows:
                player.sendLine(
                    (
                        f'  {technique["name"]}: cost {technique["stamina_cost"]} stamina; '
                        f'{_technique_effect_summary(technique)}'
                    ).encode("utf-8")
                )
            return
        result = queue_combat_technique(player.cursor, player.username, target)
        if result["status"] == "missing":
            player.sendLine(b"You do not know that technique.")
        elif result["status"] == "missing_player":
            player.sendLine(b"Your character is unavailable right now.")
        elif result["status"] == "not_engaged":
            player.sendLine(b"You must be engaged in combat to use a technique.")
        elif result["status"] == "insufficient_stamina":
            player.sendLine(
                f'You need {result["stamina_cost"]} stamina to use {result["name"]}.'.encode("utf-8")
            )
        else:
            player.sendLine(
                (
                    f'You prepare {result["name"]} for your next combat pulse. '
                    f'Stamina: {result["stamina"]}.'
                ).encode("utf-8")
            )
    except Exception as exc:
        logging.error("Unable to queue technique for %s: %s", player.username, exc, exc_info=True)
        player.sendLine(b"Unable to use that technique right now.")


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
        categories = load_command_categories(
            ACTIVE_CONFIG.get("command_categories_file", DEFAULT_CATEGORY_FILE)
        )
        catalog = load_help_catalog(ACTIVE_CONFIG.get("help_file", DEFAULT_HELP_FILE))
        player.sendLine(b"Available Commands")
        listed_commands = set()
        for label, command_names in categories.items():
            visible = [
                name for name in command_names
                if name in COMMAND_REGISTRY
                and name not in listed_commands
                and _can_see_command(player, COMMAND_REGISTRY[name])
            ]
            if not visible:
                continue
            player.sendLine(
                presentation.command_header(label, getattr(player, "color_enabled", False)).encode("utf-8")
            )
            listed_commands.update(visible)
            for name in visible:
                entry = command_help(COMMAND_REGISTRY[name], ACTIVE_CONFIG.get("help_file", DEFAULT_HELP_FILE), catalog)
                rendered_name = presentation.command_name(name, getattr(player, "color_enabled", False))
                player.sendLine(f"  {rendered_name}: {entry['summary']}".encode("utf-8"))
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
    if not _can_see_command(player, command):
        player.sendLine(f"No help found for: {topic}".encode("utf-8"))
        return

    help_entry = command_help(command, ACTIVE_CONFIG.get("help_file", DEFAULT_HELP_FILE))
    rendered_name = presentation.command_name(command.name, getattr(player, "color_enabled", False))
    rendered_usage = presentation.command_usage(command.usage, getattr(player, "color_enabled", False))
    player.sendLine(f"{rendered_name}: {help_entry['summary']}".encode("utf-8"))
    player.sendLine(f"Usage: {rendered_usage}".encode("utf-8"))
    if command.aliases:
        player.sendLine(f"Aliases: {', '.join(command.aliases)}".encode("utf-8"))
    for line in help_entry["details"]:
        player.sendLine(line.encode("utf-8"))


def handle_commands(player):
    """Display the complete command catalog from registered metadata."""
    help_file = ACTIVE_CONFIG.get("help_file", DEFAULT_HELP_FILE)
    catalog = load_help_catalog(help_file)
    categories = load_command_categories(
        ACTIVE_CONFIG.get("command_categories_file", DEFAULT_CATEGORY_FILE)
    )
    grouped_commands = []
    listed_commands = set()
    for label, command_names in categories.items():
        visible_names = [
            name
            for name in command_names
            if name in COMMAND_REGISTRY and name not in listed_commands
        ]
        if visible_names:
            grouped_commands.append((label, visible_names))
            listed_commands.update(visible_names)
    remaining_commands = sorted(set(COMMAND_REGISTRY) - listed_commands)
    if remaining_commands:
        grouped_commands.append(("Other", remaining_commands))

    player.sendLine(b"Command Catalog")
    for label, command_names in grouped_commands:
        player.sendLine(
            presentation.command_header(label, getattr(player, "color_enabled", False)).encode("utf-8")
        )
        for name in command_names:
            command = COMMAND_REGISTRY[name]
            help_entry = command_help(command, help_file, catalog)
            permission = f" [{command.permission}]" if command.permission in {"admin", "builder"} else ""
            aliases = f" (aliases: {', '.join(command.aliases)})" if command.aliases else ""
            rendered_usage = presentation.command_usage(command.usage, getattr(player, "color_enabled", False))
            player.sendLine(
                f"  {rendered_usage}{permission} - {help_entry['summary']}{aliases}".encode("utf-8")
            )
    player.sendLine(b"Use help <command> for detailed usage.")


def _can_see_command(player, command):
    """Return whether a player may see focused help for a command."""
    if command.permission == "player":
        return True
    if command.permission == "builder":
        return player.is_admin or getattr(player, "is_builder", False)
    if command.permission == "admin":
        return player.is_admin
    return False


COMMANDS = {
    "look": CommandSpec("look", lambda player, rooms, raw, args: handle_look(player, rooms, raw), "look [at <item>]", "Display your location or inspect an item.", args_validator=lambda args: not args or (len(args) >= 2 and args[0].lower() == "at")),
    "score": CommandSpec("score", lambda player, rooms, raw, args: handle_score(player, rooms), "score", "Display your character sheet.", aliases=("status",), max_args=0),
    "description": CommandSpec("description", lambda player, rooms, raw, args: handle_description(player, raw), "description [text]", "View or update your character description.", aliases=("desc",)),
    "loc": CommandSpec("loc", lambda player, rooms, raw, args: handle_loc(player), "loc", "Display your grid coordinates and area.", max_args=0),
    "who": CommandSpec("who", lambda player, rooms, raw, args: handle_who(player, rooms), "who", "List connected characters.", max_args=0),
    "survey": CommandSpec("survey", lambda player, rooms, raw, args: handle_survey(player), "survey", "Display a wide terrain view.", max_args=0),
    "color": CommandSpec("color", lambda player, rooms, raw, args: handle_color(player, raw), "color <on|off>", "Toggle ANSI terminal colors for this connection.", min_args=1, max_args=1),
    "suggest": CommandSpec("suggest", lambda player, rooms, raw, args: handle_feedback(player, raw, "suggestions_file", DEFAULT_SUGGESTIONS_FILE, "suggest", "Suggested", "Suggestion recorded."), "suggest <message>", "Record a player suggestion for builders and maintainers.", min_args=1),
    "bug": CommandSpec("bug", lambda player, rooms, raw, args: handle_feedback(player, raw, "bugs_file", DEFAULT_BUGS_FILE, "bug", "Reported", "Bug report recorded."), "bug <message>", "Record a player-visible bug report.", min_args=1),
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
    "prac": CommandSpec("prac", lambda player, rooms, raw, args: handle_practice(player, raw, "skill"), "prac [skill]", "Practice a skill or list available skills.", max_args=2),
    "train": CommandSpec("train", lambda player, rooms, raw, args: handle_practice(player, raw, "jutsu"), "train [jutsu]", "Train a jutsu or list available jutsus.", max_args=3),
    "skill": CommandSpec("skill", lambda player, rooms, raw, args: handle_progression(player, raw, "skill", allow_all=True), "skill [all|skill]", "List available skills, inspect one, or show the full catalog.", max_args=2),
    "jutsu": CommandSpec("jutsu", lambda player, rooms, raw, args: handle_progression(player, raw, "jutsu", allow_all=True), "jutsu [all|jutsu]", "List available jutsus, inspect one, or show the full catalog.", max_args=3),
    "usejutsu": CommandSpec("usejutsu", lambda player, rooms, raw, args: handle_usejutsu(player, raw), "usejutsu <jutsu>", "Activate an implemented jutsu.", min_args=1, max_args=3),
    "talk": CommandSpec("talk", lambda player, rooms, raw, args: handle_talk(player, raw), "talk <character>", "Talk to a character at your location.", min_args=1),
    "consider": CommandSpec("consider", lambda player, rooms, raw, args: handle_consider(player, raw), "consider <character>", "Inspect a character's combat details.", min_args=1),
    "attack": CommandSpec("attack", lambda player, rooms, raw, args: handle_attack(player, raw), "attack <character>", "Engage a hostile character for pulse combat.", min_args=1),
    "combat": CommandSpec("combat", lambda player, rooms, raw, args: handle_combat(player), "combat", "Display your active combat engagement and stance.", max_args=0),
    "stance": CommandSpec("stance", lambda player, rooms, raw, args: handle_stance(player, raw), "stance [s1|s2|s3|s4|s5]", "List or change your combat stance.", max_args=2),
    "technique": CommandSpec("technique", lambda player, rooms, raw, args: handle_technique(player, raw), "technique [technique]", "List or queue a stamina-based fighting technique.", max_args=2),
    "strike": CommandSpec("strike", lambda player, rooms, raw, args: handle_technique(player, "strike"), "strike", "Queue Strike for the next combat pulse.", max_args=0),
    "guard": CommandSpec("guard", lambda player, rooms, raw, args: handle_technique(player, "guard"), "guard", "Queue Guard for the next combat pulse.", max_args=0),
    "feint": CommandSpec("feint", lambda player, rooms, raw, args: handle_technique(player, "feint"), "feint", "Queue Feint for the next combat pulse.", max_args=0),
    "recover": CommandSpec("recover", lambda player, rooms, raw, args: handle_technique(player, "recover"), "recover", "Queue Recover for the next combat pulse.", max_args=0),
    "throw": CommandSpec("throw", lambda player, rooms, raw, args: handle_throw(player, raw), "throw <item> at <character>", "Throw a carried ranged item at a nearby hostile character.", min_args=3, args_validator=lambda args: "at" in [arg.lower() for arg in args]),
    "north": CommandSpec("north", lambda player, rooms, raw, args: handle_movement(player, "north"), "north", "Move north.", max_args=0),
    "south": CommandSpec("south", lambda player, rooms, raw, args: handle_movement(player, "south"), "south", "Move south.", max_args=0),
    "east": CommandSpec("east", lambda player, rooms, raw, args: handle_movement(player, "east"), "east", "Move east.", max_args=0),
    "west": CommandSpec("west", lambda player, rooms, raw, args: handle_movement(player, "west"), "west", "Move west.", max_args=0),
    "northeast": CommandSpec("northeast", lambda player, rooms, raw, args: handle_movement(player, "northeast"), "northeast", "Move northeast.", aliases=("ne",), max_args=0),
    "northwest": CommandSpec("northwest", lambda player, rooms, raw, args: handle_movement(player, "northwest"), "northwest", "Move northwest.", aliases=("nw",), max_args=0),
    "southeast": CommandSpec("southeast", lambda player, rooms, raw, args: handle_movement(player, "southeast"), "southeast", "Move southeast.", aliases=("se",), max_args=0),
    "southwest": CommandSpec("southwest", lambda player, rooms, raw, args: handle_movement(player, "southwest"), "southwest", "Move southwest.", aliases=("sw",), max_args=0),
    "help": CommandSpec("help", lambda player, rooms, raw, args: handle_help(player, raw), "help [command]", "List commands or explain one command.", max_args=1),
    "commands": CommandSpec("commands", lambda player, rooms, raw, args: handle_commands(player), "commands", "List every command with a brief description.", max_args=0),
}

