import logging
from locations import coordinate_key, online_players

logging.info("social_commands imported")

def handle_say(player, raw_args, split_args, players_in_rooms):
    message = raw_args.strip()
    if not message:
        player.sendLine(b"You must specify a message.")
        return
    
    room_key = coordinate_key(player.x, player.y)
    logging.info("Player %s used say at %s.", player.username, room_key)
    for recipient in players_in_rooms.get(room_key, [player]):
        recipient.sendLine(f'{player.username} says, "{message}"'.encode("utf-8"))

def handle_ooc(player, raw_args, split_args, players_in_rooms):
    message = raw_args.strip()
    if not message:
        player.sendLine(b"You must specify a message.")
        return

    logging.info("Player %s used ooc.", player.username)
    if not isinstance(players_in_rooms, dict):
        player.sendLine(b"Error: Invalid room data.")
        logging.error("players_in_rooms is not a dictionary.")
        return

    for recipient in online_players(players_in_rooms):
        recipient.sendLine(f"[OOC] {player.username}: {message}".encode("utf-8"))
            
def handle_think(player, raw_args, split_args, players_in_rooms):
    logging.info("Player %s used think.", player.username)
    room_key = coordinate_key(player.x, player.y)
    for recipient in players_in_rooms.get(room_key, [player]):
        recipient.sendLine(f"{player.username} thinks deeply.".encode("utf-8"))

def handle_emote(player, raw_args, split_args, players_in_rooms):
    action = raw_args.strip()
    if not action:
        player.sendLine(b"You must specify an action.")
        return

    logging.info("Player %s used emote.", player.username)
    room_key = coordinate_key(player.x, player.y)
    for recipient in players_in_rooms.get(room_key, [player]):
        recipient.sendLine(f"{player.username} {action}".encode("utf-8"))

COMMANDS = {
    "say": lambda player, players_in_rooms, raw_args, split_args: handle_say(player, raw_args, split_args, players_in_rooms),
    "ooc": lambda player, players_in_rooms, raw_args, split_args: handle_ooc(player, raw_args, split_args, players_in_rooms),
    "emote": lambda player, players_in_rooms, raw_args, split_args: handle_emote(player, raw_args, split_args, players_in_rooms),
    "think": lambda player, players_in_rooms, raw_args, split_args: handle_think(player, raw_args, split_args, players_in_rooms),
}

