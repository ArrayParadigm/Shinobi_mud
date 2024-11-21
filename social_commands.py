import logging
logging.info("social_commands imported")

def handle_say(player, raw_args, split_args, players_in_rooms):
    if not raw_args.strip():  # Check for empty message
        player.sendLine(b"You must specify a message.")
        return

    room_key = player.current_room
    if room_key in players_in_rooms:
        for recipient in players_in_rooms[room_key]:
            recipient.sendLine(f'{player.username} says, "{raw_args.strip()}"'.encode('utf-8'))
    else:
        player.sendLine(b"No one else is here to hear you.")

def handle_ooc(player, raw_args, split_args, players_in_rooms):
    if not raw_args.strip():  # Check for empty message
        player.sendLine(b"You must specify a message.")
        return

    # Validate players_in_rooms is a dictionary
    if not isinstance(players_in_rooms, dict):
        player.sendLine(b"Error: Invalid room data.")
        logging.error("players_in_rooms is not a dictionary.")
        return

    for player_list in players_in_rooms.values():
        for recipient in player_list:
            recipient.sendLine(f'({player.username}) {raw_args.strip()}'.encode('utf-8'))

def handle_emote(player, raw_args, split_args, players_in_rooms):
    if not raw_args.strip():  # Check for empty action
        player.sendLine(b"You must specify an action.")
        return

    room_key = player.current_room
    if room_key in players_in_rooms:
        for recipient in players_in_rooms[room_key]:
            recipient.sendLine(f'{player.username} {raw_args.strip()}'.encode('utf-8'))
    else:
        player.sendLine(b"No one else is here to see your action.")

COMMANDS = {
    "say": lambda player, players_in_rooms, raw_args, split_args: handle_say(player, raw_args, split_args, players_in_rooms),
    "ooc": lambda player, players_in_rooms, raw_args, split_args: handle_ooc(player, raw_args, split_args, players_in_rooms),
    "emote": lambda player, players_in_rooms, raw_args, split_args: handle_emote(player, raw_args, split_args, players_in_rooms),
}
