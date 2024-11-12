
import json
import os

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """Create a new zone as a JSON file in a subdirectory."""
    try:
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        
        # Define the subdirectory path (e.g., 'zones' folder)
        zone_directory = os.path.join("zones")
        
        # Ensure the directory exists
        os.makedirs(zone_directory, exist_ok=True)
        
        # Create the full path for the zone file
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")
        
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
        
        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum} in 'zones' directory.".encode('utf-8'))
    except ValueError:
        protocol.sendLine(b"VNUMs must be integers.")

def goto(protocol, vnum):
    """Move to a room by VNUM."""
    try:
        vnum = int(vnum)
        zone_file = find_zone_by_vnum(vnum)
        
        if not zone_file:
            protocol.sendLine(b"VNUM not found in any zone.")
            return
        
        with open(zone_file, "r") as file:
            zone_data = json.load(file)
        
        if str(vnum) not in zone_data["rooms"]:
            zone_data["rooms"][str(vnum)] = {"description": "Void room", "exits": {}}
            with open(zone_file, "w") as file:
                json.dump(zone_data, file, indent=4)
        
        protocol.current_room = vnum
        protocol.sendLine(f"Moved to room {vnum} in zone {zone_data['name']}".encode('utf-8'))
    except ValueError:
        protocol.sendLine(b"Invalid VNUM.")

def dig(protocol, direction, room_name):
    """Create a new room in the current zone and link it."""
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
    
    zone_data["rooms"][str(new_vnum)] = {"description": room_name, "exits": {}}
    zone_data["rooms"][str(vnum)]["exits"][direction] = new_vnum
    
    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)
    
    protocol.sendLine(f"Room '{room_name}' created at {new_vnum} to the {direction}".encode('utf-8'))

def edit(protocol, attribute, target, *args):
    """Edit room attributes like description or exits."""
    vnum = protocol.current_room
    zone_file = find_zone_by_vnum(vnum)
    
    if not zone_file:
        protocol.sendLine(b"Current room is not in a valid zone.")
        return
    
    with open(zone_file, "r") as file:
        zone_data = json.load(file)
    
    if str(vnum) not in zone_data["rooms"]:
        protocol.sendLine(b"Room not found in zone.")
        return
    
    room = zone_data["rooms"][str(vnum)]
    
    if attribute == "desc":
        room["description"] = target
        protocol.sendLine(b"Description updated.")
    elif attribute == "exit":
        action, direction = target, args[0]
        if action == "remove":
            room["exits"].pop(direction, None)
            protocol.sendLine(f"Exit {direction} removed.".encode('utf-8'))
        else:
            room["exits"][direction] = int(args[1])
            protocol.sendLine(f"Exit {direction} set to {args[1]}.".encode('utf-8'))
    
    with open(zone_file, "w") as file:
        json.dump(zone_data, file, indent=4)

def remove_room(protocol, vnum):
    """Remove a room from the zone."""
    vnum = str(vnum)
    zone_file = find_zone_by_vnum(vnum)
    
    if not zone_file:
        protocol.sendLine(b"Room not found in any zone.")
        return
    
    with open(zone_file, "r") as file:
        zone_data = json.load(file)
    
    if vnum in zone_data["rooms"]:
        del zone_data["rooms"][vnum]
        with open(zone_file, "w") as file:
            json.dump(zone_data, file, indent=4)
        protocol.sendLine(f"Room {vnum} removed.".encode('utf-8'))
    else:
        protocol.sendLine(b"Room not found.")

def find_zone_by_vnum(vnum):
    """Find the zone JSON file for a given VNUM."""
    zone_directory = os.path.join("zones")
    for file_name in os.listdir(zone_directory):
        if file_name.endswith('.json'):
            with open(os.path.join(zone_directory, file_name), "r") as file:
                zone_data = json.load(file)
                if zone_data["range"]["start"] <= vnum <= zone_data["range"]["end"]:
                    return os.path.join(zone_directory, file_name)
    return None

def next_free_vnum(zone_data):
    """Find the next available VNUM in the zone."""
    start, end = zone_data["range"]["start"], zone_data["range"]["end"]
    for vnum in range(start, end + 1):
        if str(vnum) not in zone_data["rooms"]:
            return vnum
    return None

def handle_shutdown(protocol):
    protocol.sendLine(b"Shutting down the server...")
    reactor.stop()

COMMANDS = {
    "shutdown": handle_shutdown,
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
    "goto": lambda protocol, players_in_rooms, *args: goto(protocol, *args),
    "dig": lambda protocol, players_in_rooms, *args: dig(protocol, *args),
    "edit": lambda protocol, players_in_rooms, *args: edit(protocol, *args),
    "removeroom": lambda protocol, players_in_rooms, *args: remove_room(protocol, *args),
}
