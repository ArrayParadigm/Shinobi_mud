"""ANSI presentation helpers for terminal clients."""

import re


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
BRIGHT_RED = "\x1b[91m"
BRIGHT_YELLOW = "\x1b[93m"
BRIGHT_CYAN = "\x1b[96m"

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
ANSI_ESCAPE_SEQUENCE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def style(text, *codes, enabled=False):
    """Wrap text in ANSI codes when color is enabled."""
    if not enabled or not codes:
        return str(text)
    return f"{''.join(codes)}{text}{RESET}"


def sanitize_player_text(text):
    """Remove terminal control characters from player-authored output."""
    return CONTROL_CHARACTERS.sub("", ANSI_ESCAPE_SEQUENCE.sub("", text))


def room_title(text, enabled=False):
    return style(text, BOLD, BRIGHT_CYAN, enabled=enabled)


def section(label, value, enabled=False):
    return f"{style(label, BOLD, CYAN, enabled=enabled)}: {value}"


def command_header(label, enabled=False):
    """Style a command-catalog section without affecting plain-text clients."""
    return style(f"== {label} ==", BOLD, BRIGHT_CYAN, enabled=enabled)


def divider(label="Nearby", enabled=False):
    """Render a readable divider without changing plain-text clients."""
    return style(f"-- {label} --", DIM, enabled=enabled)


def command_name(name, enabled=False):
    """Style a command token while leaving argument text separate."""
    return style(name, BOLD, BRIGHT_CYAN, enabled=enabled)


def command_usage(usage, enabled=False):
    """Style command names and arguments distinctly in usage strings."""
    parts = str(usage).split(maxsplit=1)
    if not parts:
        return ""
    if len(parts) == 1:
        return command_name(parts[0], enabled)
    return f"{command_name(parts[0], enabled)} {style(parts[1], DIM, enabled=enabled)}"


def prompt(health, max_health, stamina, max_stamina, chakra, max_chakra, location, enabled=False):
    """Render a compact resource prompt."""
    health_text = style(f"HP:{health}/{max_health}", BRIGHT_RED, enabled=enabled)
    stamina_text = style(f"ST:{stamina}/{max_stamina}", GREEN, enabled=enabled)
    chakra_text = style(f"CH:{chakra}/{max_chakra}", BRIGHT_CYAN, enabled=enabled)
    location_text = style(location, DIM, enabled=enabled)
    return f"[{health_text} {stamina_text} {chakra_text} | {location_text}]"


def map_symbol(symbol, enabled=False):
    """Color only map symbols with strong gameplay meaning."""
    if symbol == "P":
        return style(symbol, BOLD, BRIGHT_YELLOW, enabled=enabled)
    if symbol == "@":
        return style(symbol, BOLD, YELLOW, enabled=enabled)
    if symbol == "N":
        return style(symbol, BOLD, MAGENTA, enabled=enabled)
    if symbol == "#":
        return style(symbol, CYAN, enabled=enabled)
    if symbol == "?":
        return style(symbol, RED, enabled=enabled)
    return symbol


def legend(enabled=False):
    player = map_symbol("P", enabled)
    other_player = map_symbol("@", enabled)
    npc = map_symbol("N", enabled)
    authored_area = map_symbol("#", enabled)
    return f"Legend: {player}=you  {other_player}=player  {npc}=NPC  {authored_area}=authored area"


def ooc_message(username, message, enabled=False):
    """Style OOC metadata while keeping player-authored text unstyled."""
    channel = style("[OOC]", BOLD, MAGENTA, enabled=enabled)
    author = style(username, BOLD, enabled=enabled)
    return f"{channel} {author}: {sanitize_player_text(message)}"


def say_message(username, message, enabled=False):
    """Style speaker metadata while keeping player-authored text unstyled."""
    author = style(username, BOLD, enabled=enabled)
    return f'{author} says, "{sanitize_player_text(message)}"'


def emote_message(username, action, enabled=False):
    """Style actor metadata while keeping player-authored text unstyled."""
    author = style(username, BOLD, enabled=enabled)
    return f"{author} {sanitize_player_text(action)}"


def whisper_message(username, message, incoming=False, enabled=False):
    """Style private-message metadata while keeping authored text unstyled."""
    direction = "from" if incoming else "to"
    channel = style("[Whisper]", BOLD, MAGENTA, enabled=enabled)
    author = style(username, BOLD, enabled=enabled)
    return f"{channel} {direction} {author}: {sanitize_player_text(message)}"


def shout_message(username, message, enabled=False):
    """Style shout metadata while keeping authored text unstyled."""
    author = style(username, BOLD, enabled=enabled)
    return f'{author} shouts, "{sanitize_player_text(message)}"'
