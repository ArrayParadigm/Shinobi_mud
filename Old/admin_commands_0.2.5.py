
import json
import os
from twisted.internet import reactor

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """Create a new zone as a JSON file."""
    # Function implementation as above

def goto(protocol, vnum):
    """Move to a room by VNUM."""
    # Function implementation as above

def dig(protocol, direction, room_name):
    """Create a new room and link it."""
    # Function implementation as above

def handle_shutdown(protocol):
    """Shut down the server safely."""
    protocol.sendLine(b"Shutting down the server...")
    reactor.stop()

COMMANDS = {
    "shutdown": handle_shutdown,
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: goto <vnum>"),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args[0].split(maxsplit=1)) if len(args) == 1 else protocol.sendLine(b"Usage: dig <direction> <room_name>"),
    "edit": lambda protocol, players_in_rooms, *args: edit(protocol, *args[0].split(maxsplit=2)) if len(args) == 1 else protocol.sendLine(b"Usage: edit <attribute> <target> [additional args]"),
    "removeroom": lambda protocol, players_in_rooms, *args: remove_room(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: removeroom <vnum>"),
    "listrooms": lambda protocol, players_in_rooms: list_rooms(protocol),
}
