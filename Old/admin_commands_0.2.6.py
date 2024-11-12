
import json
import os
import logging

def create_zone(protocol, zone_name, start_vnum, end_vnum):
    """Create a new zone as a JSON file in a subdirectory."""
    try:
        start_vnum, end_vnum = int(start_vnum), int(end_vnum)
        
        # Define the subdirectory path (e.g., 'zones' folder)
        zone_directory = os.path.join("zones")
        os.makedirs(zone_directory, exist_ok=True)
        
        # Create the full path for the zone file
        zone_file_path = os.path.join(zone_directory, f"{zone_name}.json")
        logging.info(f"Attempting to create zone file at: {zone_file_path}")

        if os.path.exists(zone_file_path):
            protocol.sendLine(b"Zone already exists.")
            logging.warning(f"Zone creation failed: {zone_file_path} already exists.")
            return
        
        zone_data = {
            "name": zone_name,
            "range": {"start": start_vnum, "end": end_vnum},
            "rooms": {}
        }
        
        with open(zone_file_path, "w") as zone_file:
            json.dump(zone_data, zone_file, indent=4)
        
        protocol.sendLine(f"Zone {zone_name} created with VNUM range {start_vnum}-{end_vnum} in 'zones' directory.".encode('utf-8'))
        logging.info(f"Zone {zone_name} successfully created with range {start_vnum}-{end_vnum}.")

    except ValueError as ve:
        protocol.sendLine(b"VNUMs must be integers.")
        logging.error(f"ValueError in create_zone: {ve}")
    except Exception as e:
        protocol.sendLine(b"An error occurred while creating the zone.")
        logging.error(f"Unhandled exception in create_zone: {e}", exc_info=True)

# Updated command set with enhanced create_zone
COMMANDS = {
    "createzone": lambda protocol, players_in_rooms, *args: create_zone(protocol, *args[0].split()) if len(args) == 1 else protocol.sendLine(b"Usage: createzone <zone_name> <start_vnum> <end_vnum>"),
}
