import logging
from command_system import CommandSpec
from locations import coordinate_key, online_players
from presentation import emote_message, ooc_message, say_message, shout_message, whisper_message
from socials import (
    CONSENT_ALLOW,
    CONSENT_DENY,
    STATE_RESTRAINED,
    active_social_states,
    can_see_social,
    clear_social_state,
    clear_social_states,
    consent_summary,
    create_social_state,
    format_social_message,
    has_consent,
    list_socials,
    normalize_key,
    revoke_consent,
    set_consent,
    social_template,
)

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


def handle_socials(player, raw_args, split_args, players_in_rooms):
    """List available catalog-backed socials."""
    category = split_args[0] if split_args else None
    try:
        rows = list_socials(player.cursor, player.username, category)
    except ValueError as exc:
        player.sendLine(str(exc).encode("utf-8"))
        return

    if not rows:
        player.sendLine(b"No socials are visible in that category.")
        return

    current_category = None
    for row in rows:
        if row["category"] != current_category:
            current_category = row["category"]
            player.sendLine(f"== {current_category.title()} Socials ==".encode("utf-8"))
        flags = []
        if row["requires_consent"]:
            flags.append("consent")
        if row["adult"]:
            flags.append("adult")
        if row["mechanical"]:
            flags.append(row["mechanical"])
        suffix = f" ({', '.join(flags)})" if flags else ""
        player.sendLine(f"  {row['social_key']}{suffix}".encode("utf-8"))
    player.sendLine(b"Use consent to manage intimate, BDSM, mechanical, and restrictive social access.")


def handle_consent(player, raw_args, split_args, players_in_rooms):
    """Inspect or update social consent settings."""
    if not split_args:
        states, players = consent_summary(player.cursor, player.username)
        player.sendLine(b"Social consent settings")
        for category, state in states.items():
            player.sendLine(f"  {category}: {state}".encode("utf-8"))
        if players:
            player.sendLine(b"Player-specific consent")
            for line in players:
                player.sendLine(f"  {line}".encode("utf-8"))
        player.sendLine(b"Use consent allow|deny <category> [player], or consent revoke <player>.")
        return

    action = normalize_key(split_args[0])
    if action == "revoke":
        if len(split_args) != 2:
            player.sendLine(b"Usage: consent revoke <character>")
            return
        try:
            revoke_consent(player.cursor, player.username, split_args[1])
        except ValueError as exc:
            player.sendLine(str(exc).encode("utf-8"))
            return
        player.sendLine(f"Revoked player-specific social consent for {split_args[1]}.".encode("utf-8"))
        return

    if action not in {CONSENT_ALLOW, CONSENT_DENY} or len(split_args) not in {2, 3}:
        player.sendLine(b"Usage: consent [allow|deny <category> [character] | revoke <character>]")
        return
    category = normalize_key(split_args[1])
    target = split_args[2] if len(split_args) == 3 else ""
    try:
        set_consent(player.cursor, player.username, category, action, target)
    except ValueError as exc:
        player.sendLine(str(exc).encode("utf-8"))
        return

    target_text = f" for {target}" if target else ""
    player.sendLine(f"Consent {action} set for {category}{target_text}.".encode("utf-8"))


def handle_catalog_social(player, raw_args, split_args, players_in_rooms, social_key):
    """Run one authored social action."""
    template = social_template(player.cursor, social_key)
    if not template or not can_see_social(player.cursor, player.username, template):
        player.sendLine(f"Unknown social: {social_key}".encode("utf-8"))
        return
    target = None
    if template["target_required"]:
        if not split_args:
            player.sendLine(f"Usage: {social_key} <character>".encode("utf-8"))
            return
        target = _online_player_at_location(player, split_args[0], players_in_rooms)
        if not target:
            player.sendLine(f"Character not here: {split_args[0]}".encode("utf-8"))
            return
        if target is player:
            player.sendLine(b"That social needs another character.")
            return
        mechanical = template["mechanical"]
        if template["requires_consent"] and not has_consent(
            player.cursor,
            player.username,
            target.username,
            template["category"],
            mechanical,
        ):
            player.sendLine(
                f"{target.username} has not consented to {template['category']} socials from you.".encode("utf-8")
            )
            return

    _broadcast_social(player, target, template, players_in_rooms)
    if target and template["mechanical"]:
        create_social_state(player.cursor, template["mechanical"], player.username, target.username)
        player.cursor.connection.commit()


def handle_release(player, raw_args, split_args, players_in_rooms):
    """Release active social states controlled by the player."""
    if not split_args:
        player.sendLine(b"Usage: release <character|all>")
        return
    target_name = split_args[0]
    if normalize_key(target_name) == "all":
        rows = active_social_states(player.cursor, player.username)
        released = sorted({row["target"] for row in rows if row["actor"] == player.username})
        clear_social_states(player.cursor, player.username)
        player.cursor.connection.commit()
        player.sendLine(b"Released all social states you controlled.")
        for target in released:
            online_target = _online_player(players_in_rooms, target)
            if online_target:
                online_target.sendLine(f"{player.username} releases you.".encode("utf-8"))
        return

    target = _online_player(players_in_rooms, target_name)
    if not target:
        player.sendLine(f"Online player not found: {target_name}".encode("utf-8"))
        return
    clear_social_states(player.cursor, player.username, target.username)
    player.cursor.connection.commit()
    player.sendLine(f"You release {target.username}.".encode("utf-8"))
    target.sendLine(f"{player.username} releases you.".encode("utf-8"))


def handle_resist(player, raw_args, split_args, players_in_rooms):
    """Break active restrictive states on yourself."""
    rows = [
        row
        for row in active_social_states(player.cursor, player.username)
        if row["target"] == player.username and row["state_type"] == STATE_RESTRAINED
    ]
    if not rows:
        player.sendLine(b"You are not restrained.")
        return
    for row in rows:
        clear_social_state(player.cursor, STATE_RESTRAINED, row["actor"], player.username)
        actor = _online_player(players_in_rooms, row["actor"])
        if actor:
            actor.sendLine(f"{player.username} resists free from your restraint.".encode("utf-8"))
    player.cursor.connection.commit()
    player.sendLine(b"You resist free from the restraint.")


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


def _broadcast_social(actor, target, template, players_in_rooms):
    room_key = coordinate_key(actor.x, actor.y)
    actor_message = format_social_message(template, "actor_message", actor, target)
    target_message = format_social_message(template, "target_message", actor, target)
    room_message = format_social_message(template, "room_message", actor, target)
    self_message = format_social_message(template, "self_message", actor, target)
    for recipient in players_in_rooms.get(room_key, [actor]):
        if recipient is actor:
            message = actor_message or self_message or room_message
        elif target is not None and recipient is target:
            message = target_message or room_message
        else:
            message = room_message
        if message:
            recipient.sendLine(message.encode("utf-8"))


def _online_player(players_in_rooms, username):
    for player in online_players(players_in_rooms):
        if player.username.casefold() == username.casefold():
            return player
    return None


def _online_player_at_location(player, username, players_in_rooms):
    room_key = coordinate_key(player.x, player.y)
    for candidate in players_in_rooms.get(room_key, []):
        if candidate.username.casefold() == username.casefold():
            return candidate
    return None


def _social_command(name):
    return CommandSpec(
        name,
        lambda player, rooms, raw, args, social_key=name: handle_catalog_social(
            player,
            raw,
            args,
            rooms,
            social_key,
        ),
        f"{name} [character]",
        f"Perform the {name} social.",
        min_args=0,
        max_args=1,
    )


COMMANDS = {
    "say": CommandSpec("say", lambda player, rooms, raw, args: handle_say(player, raw, args, rooms), "say <message>", "Speak to characters at your location.", min_args=1),
    "ooc": CommandSpec("ooc", lambda player, rooms, raw, args: handle_ooc(player, raw, args, rooms), "ooc <message>", "Speak on the global out-of-character channel.", min_args=1),
    "emote": CommandSpec("emote", lambda player, rooms, raw, args: handle_emote(player, raw, args, rooms), "emote <action>", "Perform an action at your location.", min_args=1),
    "think": CommandSpec("think", lambda player, rooms, raw, args: handle_think(player, raw, args, rooms), "think", "Perform the built-in thinking emote.", max_args=0),
    "whisper": CommandSpec("whisper", lambda player, rooms, raw, args: handle_whisper(player, raw, args, rooms), "whisper <character> <message>", "Send a private message to an online character.", min_args=2),
    "shout": CommandSpec("shout", lambda player, rooms, raw, args: handle_shout(player, raw, args, rooms), "shout <message>", "Speak to characters within one grid cell.", min_args=1),
    "socials": CommandSpec("socials", lambda player, rooms, raw, args: handle_socials(player, raw, args, rooms), "socials [category|all]", "List catalog-backed social actions.", max_args=1),
    "consent": CommandSpec("consent", lambda player, rooms, raw, args: handle_consent(player, raw, args, rooms), "consent [allow|deny <category> [character] | revoke <character>]", "Manage social consent settings.", max_args=3),
    "release": CommandSpec("release", lambda player, rooms, raw, args: handle_release(player, raw, args, rooms), "release <character|all>", "Release social holds or restraints you control.", min_args=1, max_args=1),
    "resist": CommandSpec("resist", lambda player, rooms, raw, args: handle_resist(player, raw, args, rooms), "resist", "Break an active restrictive social state on yourself.", max_args=0),
}

for social_name in (
    "wave",
    "smile",
    "nod",
    "bow",
    "laugh",
    "hug",
    "highfive",
    "pat",
    "poke",
    "cuddle",
    "nuzzle",
    "holdhands",
    "tie",
    "restrain",
    "kneel",
):
    COMMANDS[social_name] = _social_command(social_name)

