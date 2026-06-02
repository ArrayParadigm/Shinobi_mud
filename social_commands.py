import logging
from command_system import CommandSpec
from locations import coordinate_key, online_players
from presentation import emote_message, ooc_message, say_message, shout_message, whisper_message

logging.info("social_commands imported")

def handle_say(player, raw_args, split_args, players_in_rooms):
    message = raw_args.strip()
    if not message:
        player.sendLine(b"You must specify a message.")
        return
    
    room_key = coordinate_key(player.x, player.y)
    logging.info("Player %s used say at %s.", player.username, room_key)
    for recipient in players_in_rooms.get(room_key, [player]):
        recipient.sendLine(
            say_message(
                player.username,
                message,
                getattr(recipient, "color_enabled", False),
            ).encode("utf-8")
        )

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
        recipient.sendLine(
            ooc_message(
                player.username,
                message,
                getattr(recipient, "color_enabled", False),
            ).encode("utf-8")
        )
            
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
        recipient.sendLine(
            emote_message(
                player.username,
                action,
                getattr(recipient, "color_enabled", False),
            ).encode("utf-8")
        )


def handle_whisper(player, raw_args, split_args, players_in_rooms):
    """Send one private message to an online character."""
    if len(split_args) < 2:
        player.sendLine(b"Usage: whisper <character> <message>")
        return
    target_name, message = split_args[0], raw_args.split(maxsplit=1)[1]
    target = next(
        (
            online_player
            for online_player in online_players(players_in_rooms)
            if online_player.username.casefold() == target_name.casefold()
        ),
        None,
    )
    if not target:
        player.sendLine(f"Online player not found: {target_name}".encode("utf-8"))
        return
    logging.info("Player %s used whisper to %s.", player.username, target.username)
    player.sendLine(
        whisper_message(target.username, message, enabled=getattr(player, "color_enabled", False)).encode("utf-8")
    )
    if target is not player:
        target.sendLine(
            whisper_message(player.username, message, incoming=True, enabled=getattr(target, "color_enabled", False)).encode("utf-8")
        )


def handle_shout(player, raw_args, split_args, players_in_rooms):
    """Broadcast one message to characters within one grid cell."""
    message = raw_args.strip()
    if not message:
        player.sendLine(b"You must specify a message.")
        return
    logging.info("Player %s used shout.", player.username)
    for recipient in online_players(players_in_rooms):
        distance = max(abs(recipient.x - player.x), abs(recipient.y - player.y))
        if distance <= 1:
            recipient.sendLine(
                shout_message(player.username, message, getattr(recipient, "color_enabled", False)).encode("utf-8")
            )


COMMANDS = {
    "say": CommandSpec("say", lambda player, rooms, raw, args: handle_say(player, raw, args, rooms), "say <message>", "Speak to characters at your location.", min_args=1),
    "ooc": CommandSpec("ooc", lambda player, rooms, raw, args: handle_ooc(player, raw, args, rooms), "ooc <message>", "Speak on the global out-of-character channel.", min_args=1),
    "emote": CommandSpec("emote", lambda player, rooms, raw, args: handle_emote(player, raw, args, rooms), "emote <action>", "Perform an action at your location.", min_args=1),
    "think": CommandSpec("think", lambda player, rooms, raw, args: handle_think(player, raw, args, rooms), "think", "Perform the built-in thinking emote.", max_args=0),
    "whisper": CommandSpec("whisper", lambda player, rooms, raw, args: handle_whisper(player, raw, args, rooms), "whisper <character> <message>", "Send a private message to an online character.", min_args=2),
    "shout": CommandSpec("shout", lambda player, rooms, raw, args: handle_shout(player, raw, args, rooms), "shout <message>", "Speak to characters within one grid cell.", min_args=1),
}

