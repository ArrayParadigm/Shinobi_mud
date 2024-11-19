
from admin_commands import find_zone_by_vnum
from admin_commands import ensure_room_exists

import json

def handle_look(protocol, players_in_rooms=None):
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    room = zone_data["rooms"].get(str(vnum))
    if not room:
        protocol.sendLine(b"Room not found.")
        return

    description = room["description"]
    exits = ", ".join(room["exits"].keys()) or "None"
    protocol.sendLine(f"Room {vnum}: {description}".encode('utf-8'))
    protocol.sendLine(f"Exits: {exits}".encode('utf-8'))

def handle_movement(protocol, direction):
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    current_room = zone_data["rooms"].get(str(vnum))
    if not current_room:
        protocol.sendLine(b"Current room not found in zone data.")
        return

    next_vnum = current_room.get("exits", {}).get(direction)
    if not next_vnum:
        protocol.sendLine(b"No exit in that direction.")
        return

    # Ensure target room exists before moving
    if ensure_room_exists(next_vnum, protocol):
        # Update the player's current room
        previous_room = protocol.current_room
        protocol.current_room = int(next_vnum)
        protocol.untrack_player(previous_room)
        protocol.track_player()
        protocol.cursor.execute(
            "UPDATE players SET current_room=? WHERE username=?", 
            (protocol.current_room, protocol.username)
        )
        protocol.cursor.connection.commit()
        protocol.sendLine(f"Moved to room {next_vnum}.".encode('utf-8'))
        protocol.display_room()

#    protocol.current_room = next_vnum
#    protocol.track_player()
#    protocol.cursor.execute(
#        "UPDATE players SET current_room=? WHERE username=?", 
#        (protocol.current_room, protocol.username)
#    )
#    protocol.cursor.connection.commit()
#    protocol.sendLine(f"Moved to room {next_vnum}.".encode('utf-8'))
#    protocol.display_room()

COMMANDS = {
    "look": handle_look,
    "north": lambda protocol, players_in_rooms=None: handle_movement(protocol, "north"),
    "south": lambda protocol, players_in_rooms=None: handle_movement(protocol, "south"),
    "east": lambda protocol, players_in_rooms=None: handle_movement(protocol, "east"),
    "west": lambda protocol, players_in_rooms=None: handle_movement(protocol, "west"),
}

def handle_status(protocol, players_in_rooms=None):
    try:
        protocol.cursor.execute(
            "SELECT health, stamina, chakra, strength, dexterity, agility, intelligence, wisdom, dojo_alignment "
            "FROM players WHERE username=?",
            (protocol.username,))
        stats = protocol.cursor.fetchone()
        if stats:
            protocol.sendLine(f"Stats for {protocol.username}:".encode('utf-8'))
            protocol.sendLine(f"Health: {stats[0]}, Stamina: {stats[1]}, Chakra: {stats[2]}".encode('utf-8'))
            protocol.sendLine(f"Strength: {stats[3]}, Dexterity: {stats[4]}, Agility: {stats[5]}".encode('utf-8'))
            protocol.sendLine(f"Intelligence: {stats[6]}, Wisdom: {stats[7]}, Dojo Alignment: {stats[8]}".encode('utf-8'))
        else:
            protocol.sendLine(b"No stats found for your character.")
    except Exception as e:
        protocol.sendLine(f"Error retrieving stats: {e}".encode('utf-8'))


COMMANDS.update({
    "status": lambda protocol, players_in_rooms=None: handle_status(protocol, players_in_rooms)
})
