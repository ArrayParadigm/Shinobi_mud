
import json
import os
import logging
import sys
from twisted.internet import reactor

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    try:
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        zone_directory = os.path.join("zones")
        os.makedirs(zone_directory, exist_ok=True)
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")
        logging.info(f"Creating zone file at: {zone_file_path}")

        if os.path.exists(zone_file_path):
            protocol.sendLine(b"Zone already exists.")
            return

        zone_data = {
            "name": zone_name,
            "range": {"start": start_vnum, "end": end_vnum},
            "rooms": {}
        }

        with open(zone_file_path, "w") as zone_file:
            json.dump(zone_data, zone_file, indent=4)

        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum}.".encode('utf-8'))
        logging.info(f"Zone {zone_name} created with range {start_vnum}-{end_vnum}.")

    except ValueError:
        protocol.sendLine(b"VNUMs must be integers.")

def goto(protocol, vnum):
    try:
        vnum = int(vnum)
        zone_file = find_zone_by_vnum(vnum)
        if not zone_file:
            protocol.sendLine(b"VNUM not found in any zone.")
            return

        with open(zone_file, "r") as file:
            zone_data = json.load(file)

        if str(vnum) not in zone_data["rooms"]:
            protocol.sendLine(b"Room not found. Initializing empty room.")
            zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
            with open(zone_file, "w") as file:
                json.dump(zone_data, file, indent=4)

        protocol.current_room = vnum
        protocol.sendLine(f"Moved to room {vnum} in zone {zone_data['name']}".encode('utf-8'))

    except ValueError:
        protocol.sendLine(b"Invalid VNUM.")

def dig(protocol, direction, room_name):
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"Current room not found in zone.")
        return

    new_vnum = next_free_vnum(zone_data)
    if not new_vnum:
        protocol.sendLine(b"No free VNUMs in this zone.")
        return

    # Create and link new room
    zone_data["rooms"][str(new_vnum)] = {"description": room_name, "exits": {reverse_dir(direction): vnum}}
    zone_data["rooms"][str(vnum)]["exits"][direction] = new_vnum

    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

    protocol.sendLine(f"Room '{room_name}' created at {new_vnum} to the {direction}".encode('utf-8'))

def find_zone_by_vnum(vnum):
    zone_directory = os.path.join("zones")
    for file_name in os.listdir(zone_directory):
        if file_name.endswith('.json'):
            with open(os.path.join(zone_directory, file_name), "r") as file:
                zone_data = json.load(file)
                if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                    return os.path.join(zone_directory, file_name)
    return None

def ensure_room_exists(vnum, protocol):
    cursor = protocol.cursor  # Use protocol's cursor
    zone_file = find_zone_by_vnum(vnum)
    
    if not zone_file:
        protocol.sendLine(b"Room not found in zone file.")
        return False

    with open(zone_file, "r") as file:
        zone_data = json.load(file)

    if str(vnum) not in zone_data["rooms"]:
        zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
        with open(zone_file, "w") as file:
            json.dump(zone_data, file, indent=4)
        protocol.sendLine(b"Room initialized in zone file.")

    cursor.execute("SELECT id FROM rooms WHERE id=?", (vnum,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO rooms (id, name, description, exits) VALUES (?, ?, ?, ?)",
            (vnum, f"Room {vnum}", "This room was auto-added.", "{}")
        )
        protocol.cursor.connection.commit()
        protocol.sendLine(b"Room initialized in database.")
    return True


def next_free_vnum(zone_data):
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None

def reverse_dir(direction):
    return {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "")
    
def shutdown(protocol, players_in_rooms=None):
    """Shuts down the MUD server."""
    protocol.sendLine(b"Shutting down the server...")
    logging.info(f"User {protocol.username} initiated shutdown.")
    reactor.stop()

def copyover(protocol, players_in_rooms=None):
    """Soft reboot (copyover) while saving minimal player state."""
    protocol.sendLine(b"Initiating copyover... Please hold on.")
    logging.info(f"User {protocol.username} initiated copyover.")

    # Save player room and username
    try:
        with open("copyover_state.json", "w") as f:
            state_data = {
                "players": [
                    {
                        "username": protocol.username,
                        "room": protocol.current_room,
                    }
                ]
            }
            json.dump(state_data, f)

        args = sys.argv[:]
        args.insert(0, sys.executable)
        os.execv(sys.executable, args)
    except Exception as e:
        logging.error(f"Copyover failed: {e}")
        protocol.sendLine(b"Copyover failed. Please contact an admin.")

def recover_state():
    """Recover player states after a copyover."""
    if os.path.exists("copyover_state.json"):
        with open("copyover_state.json", "r") as f:
            state_data = json.load(f)
            for player in state_data["players"]:
                # Reconnect player and place them back in their room
                logging.info(f"Restoring player {player['username']} to room {player['room']}")
                # Handle automatic login/rebinding here
        os.remove("copyover_state.json")

COMMANDS = {
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args[0].split()),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args[0].split(maxsplit=1)),
    "shutdown": shutdown,
    "copyover": copyover, 
}

def setrole(protocol, username, role_type):
    try:
        cursor.execute("UPDATE players SET role_type=? WHERE username=?", (int(role_type), username))
        conn.commit()
        protocol.sendLine(f"Set role of {username} to {role_type}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set role: {e}".encode('utf-8'))

def setstat(protocol, username, stat, value):
    try:
        if stat not in ('health', 'stamina', 'chakra', 'strength', 'dexterity', 'agility', 'intelligence', 'wisdom'):
            protocol.sendLine(b"Invalid stat.")
            return
        cursor.execute(f"UPDATE players SET {stat}=? WHERE username=?", (int(value), username))
        conn.commit()
        protocol.sendLine(f"Set {stat} of {username} to {value}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set stat: {e}".encode('utf-8'))

def setdojo(protocol, username, dojo):
    try:
        cursor.execute("UPDATE players SET dojo_alignment=? WHERE username=?", (dojo, username))
        conn.commit()
        protocol.sendLine(f"Set dojo of {username} to {dojo}".encode('utf-8'))
    except Exception as e:
        protocol.sendLine(f"Failed to set dojo: {e}".encode('utf-8'))

# Adding commands to registry
COMMANDS.update({
    "setrole": lambda protocol, players_in_rooms, *args: setrole(protocol, *args),
    "setstat": lambda protocol, players_in_rooms, *args: setstat(protocol, *args),
    "setdojo": lambda protocol, players_in_rooms, *args: setdojo(protocol, *args),
})
