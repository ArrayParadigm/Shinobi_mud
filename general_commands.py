import json
import logging
from shinobi_mud import UTILITIES

logging.info("general_commands imported")


def handle_look(player, players_in_rooms=None):
    vnum = player.current_room
    logging.debug(f"UTILITIES in general_commands: {UTILITIES.keys()}")
    zone_file = UTILITIES["find_zone_by_vnum"](vnum)  # Use UTILITIES reference
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

def handle_movement(player, direction):
    vnum = player.current_room
    zone_file = UTILITIES["find_zone_by_vnum"](vnum)  # Use UTILITIES reference
    if not zone_file:
        player.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    current_room = zone_data["rooms"].get(str(vnum))
    if not current_room:
        player.sendLine(b"Current room not found in zone data.")
        return

    next_vnum = current_room.get("exits", {}).get(direction)
    if not next_vnum:
        player.sendLine(b"No exit in that direction.")
        return

    if UTILITIES["ensure_room_exists"](next_vnum, player):  # Use UTILITIES reference
        try:
            player.current_room = int(next_vnum)
            player.track_player()  # Ensure player is tracked correctly
            player.sendLine(f"Moved to room {next_vnum}.".encode("utf-8"))
            player.display_room()  # Display the new room's details
        except Exception as e:
            logging.error(f"Error during movement: {e}", exc_info=True)
            player.sendLine(b"An error occurred while moving to the next room.")

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

COMMANDS = {
    "look": lambda player, players_in_rooms, raw_args, split_args: handle_look(player, players_in_rooms),
    "north": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "north"),
    "south": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "south"),
    "east": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "east"),
    "west": lambda player, players_in_rooms, raw_args, split_args: handle_movement(player, "west"),
    "status": lambda player, players_in_rooms, raw_args, split_args: handle_status(player, players_in_rooms),
}

