import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import logging
import importlib
import json
import inspect
import sys
from auth import hash_password, validate_username, verify_password
from locations import coordinate_key, players_at, track_player, untrack_player
from migrations import apply_migrations, create_players_table

DEBUG_MODE = True  # True allows for debugging options; False disables them
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_DB_FILE = "mud_game_10_rooms.db"
DEFAULT_MOTD = "Welcome to Ninja MUD!"
DEFAULT_PORT = 4000

# Command modules import shinobi_mud. Reuse this module when launched as a script.
sys.modules.setdefault("shinobi_mud", sys.modules[__name__])

def configure_logging(log_file="mud_debug.log"):
    """Replace root logging handlers so repeated initialization stays clean."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)


configure_logging()

COMMAND_REGISTRY = {}
UTILITIES = {}
players_in_rooms = {}
WORLD_OVERLAYS = {}

# List of explicitly approved command modules
COMMAND_MODULES = [
    "general_commands",
    "admin_commands",
    "social_commands",
    # Add new command modules here
]
           
def load_utilities(module_name="utils"):
    """Dynamically loads all functions from the specified utility module."""
    try:
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            UTILITIES[name] = obj
            logging.info(f"Loaded utility: {name}")
    except ImportError as e:
        logging.error(f"Failed to load utilities from {module_name}: {e}")
    # At the end of load_utilities
    logging.debug(f"UTILITIES after loading in shinobi_mud: {list(UTILITIES.keys())}")

#TODO: load_utilities call moved here due to timing issues from initialization. It's the intent to fix this later on when I'm further along.
load_utilities()

global WORLD_MAP
WORLD_MAP = UTILITIES['load_world_map']()  # Load the world map
UTILITIES['WORLD_MAP'] = WORLD_MAP  # Add WORLD_MAP to UTILITIES for global access

def load_commands():
    """Dynamically loads COMMANDS from explicitly listed modules."""
    for module_name in COMMAND_MODULES:
        try:
            # Import the module
            module = importlib.import_module(module_name)
            # Check if the module defines a COMMANDS dictionary
            if hasattr(module, "COMMANDS"):
                COMMAND_REGISTRY.update(module.COMMANDS)
                logging.info(f"Loaded commands from {module_name}")
            else:
                logging.warning(f"No COMMANDS dictionary in {module_name}")
        except ImportError as e:
            logging.error(f"Failed to import {module_name}: {e}")
 
logging.info(f"Total commands loaded: {len(COMMAND_REGISTRY)}")

# Add this utility function for cross-checking
def get_all_commands():
    """Aggregates all commands for cross-check validation."""
    return set(COMMAND_REGISTRY.keys())

# Cross-check command consistency during startup
ALL_COMMANDS = get_all_commands()
logging.debug(f"All registered commands: {sorted(ALL_COMMANDS)}")

# Database setup
conn = sqlite3.connect(DEFAULT_DB_FILE)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
MOTD = DEFAULT_MOTD

def debug_log(message):
    """Wrapper for debug-level logging."""
    logging.debug(message)

def preload_zones(zone_directory):
    """Preloads zone files from the specified directory and initializes database rooms."""
    for file_name in os.listdir(zone_directory):
        if file_name.endswith(".json"):
            try:
                with open(os.path.join(zone_directory, file_name), "r") as file:
                    zone_data = json.load(file)
                    logging.info(f"Preloaded zone: {zone_data['name']}")

                    # Ensure rooms are loaded into the database
                    for room_id, room_data in zone_data["rooms"].items():
                        cursor.execute(
                            '''INSERT OR IGNORE INTO rooms (id, name, description, exits) 
                            VALUES (?, ?, ?, ?)''',
                            (
                                room_id,
                                room_data.get("name", "Unnamed Room"),
                                room_data.get("description", "No description."),
                                json.dumps(room_data.get("exits", {})),
                            )
                        )
                conn.commit()
            except Exception as e:
                logging.error(f"Error preloading zone file {file_name}: {e}", exc_info=True)


def process_command(player, command):
    command = command.strip()  # Strip any leading/trailing whitespace
    
    # Split command into command and arguments
    parts = command.split(' ', 1)  # Split at the first space
    cmd = parts[0].lower()  # Extract and normalize command name
    raw_args = parts[1] if len(parts) > 1 else ""  # Extract raw argument string
    split_args = raw_args.split()  # Split arguments into a list
    
    # Debug raw_args and split_args
    logging.debug(f"Command: {cmd}, Raw Args: '{raw_args}', Split Args: {split_args}")

    # Use COMMAND_REGISTRY for all commands
    handler = COMMAND_REGISTRY.get(cmd)
    if handler:
        logging.info(f"Executing command '{cmd}' for player {player.username} with raw args '{raw_args}' and split args {split_args}")
        try:
            # Pass player, players_in_rooms, raw argument string, and split arguments
            handler(player, players_in_rooms, raw_args, split_args)
        except Exception as e:
            logging.error(f"Error executing command '{cmd}' for {player.username}: {e}", exc_info=True)
            player.sendLine(b"An error occurred while executing your command.")
    else:
        player.sendLine(f"Unknown command: {cmd}".encode('utf-8'))
        logging.warning(f"Unknown command '{cmd}' issued by player {player.username}")


def is_username_active(username, exclude=None):
    """Return True when a username is already attached to an active protocol."""
    return any(
        player is not exclude and player.username == username
        for room_players in players_in_rooms.values()
        for player in room_players
    )


def ensure_tables_exist(connection=None):
    active_connection = connection or conn
    active_cursor = active_connection.cursor()
    try:
        # Create players table if it doesn't exist
        create_players_table(active_cursor)

        debug_log("Creating player due to lack of existence.")

        # Create rooms table if it doesn't exist
        active_cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            exits TEXT
        )''')

        active_connection.commit()
        logging.info("Database tables ensured and default rooms initialized.")
        debug_log("Database tables ensured and default rooms initialized.")
    except Exception as e:
        logging.error(f"Failed to ensure database tables: {e}")
        debug_log("Failed to ensure database tables.")

logging.info("Zones loaded")
debug_log("Zones loaded after preload_zones()")

def get_state_handlers():
    return {
        "GET_USERNAME": "handle_username",
        "GET_PASSWORD": "handle_password",
        "REGISTER_PASSWORD": "register_password",
        "CONFIRM_PASSWORD": "confirm_password",
        "CHOOSE_SPECIALTY": "choose_specialty",
        "ALLOCATE_STATS": "allocate_stats",
        "COMMAND": "handle_command",
    }

class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self, cursor):
        self.cursor = cursor  # Save the cursor for database operations
        self.state = "GET_USERNAME"
        self.character_creation_data = {}
        self.username = None
        self.is_admin = False
        self.player_class = 'newbie' # Default to a basic Class
        self.STATE_HANDLERS = get_state_handlers()
        
        self.in_zone = False
        self.x = 500
        self.y = 500
                
    def connectionMade(self):
        logging.info("New connection established from %s.", self.transport.getPeer())
        debug_log("New connection established from [self.transport.getPeer()}.")
        if MOTD:
            self.sendLine(MOTD.encode('utf-8'))  # Send MOTD to the player
        else:
            self.sendLine(b"Welcome to Ninja MUD!")  # Fallback if no MOTD is set

        # Send the MOTD when the player connects
        self.sendLine(b"Please enter your username:")
        # Simplify: Initialize player to a default room if new
        self.x, self.y = 500, 500  # Default coordinates
        
    def connectionLost(self, reason):
        logging.info(f"Connection lost for user {self.username}. Reason: {reason}")
        self.untrack_player()
    
    def lineReceived(self, line):
        try:
            command = line.decode('utf-8').strip()  # Decode input and remove leading/trailing whitespace
            if self.state in {"GET_PASSWORD", "REGISTER_PASSWORD", "CONFIRM_PASSWORD"}:
                logging.info("Received redacted input in state: %s", self.state)
            else:
                logging.info("Received command: %s in state: %s", command, self.state)
        except UnicodeDecodeError:
            self.sendLine(b"Error: Invalid input encoding. Please use UTF-8.")
            logging.error("Received non-UTF-8 encoded input.", exc_info=True)
            return

        # Access STATE_HANDLERS using self or the class name
        handler_name = self.STATE_HANDLERS.get(self.state)
        if handler_name and hasattr(self, handler_name):
            try:
                handler = getattr(self, handler_name)  # Get the appropriate handler
                handler(command)  # Call the handler with the command
            except Exception as e:
                logging.error(f"Error in state {self.state}: {e}", exc_info=True)
                self.sendLine(b"An error occurred. Please try again.")
        else:
            self.sendLine(b"Unknown state.")
            logging.warning(f"Unknown state: {self.state}")

    def handle_username(self, username):
        username = username.strip()
        validation_error = validate_username(username)
        if validation_error:
            self.sendLine(validation_error.encode("utf-8"))
            self.sendLine(b"Please enter your username:")
            return

        self.username = username
        self.cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = self.cursor.fetchone()

        if player:
            self.sendLine(b"Welcome back! Please enter your password:")
            self.state = "GET_PASSWORD"
        else:
            self.sendLine(b"Username not found. Creating a new account.")
            self.sendLine(b"Choose a password:")
            self.state = "REGISTER_PASSWORD"

    def handle_password(self, password):
        self.cursor.execute("SELECT * FROM players WHERE username=?", (self.username,))
        player = self.cursor.fetchone()
        if not player:
            self.sendLine(b"Incorrect password. Try again.")
            return

        password_matches, needs_upgrade = verify_password(password, player["password"])
        if not password_matches:
            self.sendLine(b"Incorrect password. Try again.")
            return

        if is_username_active(self.username, exclude=self):
            self.sendLine(b"That character is already logged in.")
            return

        if needs_upgrade:
            self.cursor.execute(
                "UPDATE players SET password=? WHERE username=?",
                (hash_password(password), self.username),
            )
            self.cursor.connection.commit()
            logging.info("Upgraded legacy password hash for %s.", self.username)

        self.x = player["x"]
        self.y = player["y"]
        self.is_admin = bool(player["is_admin"])
        self.player_class = player["role_type"]
        self.sendLine(b"Login successful!")
        self.state = "COMMAND"
        self.track_player()
        self.display_room()
            
    def list_players_in_room(self):
        """List other players at the current world coordinate."""
        others = [player.username for player in players_at(players_in_rooms, self.x, self.y, self)]
        logging.info("User %s checking location %s. Others here: %s", self.username, self.location_key, others)
        
        if others:
            self.sendLine(f"Also here: {', '.join(others)}".encode('utf-8'))
        else:
            self.sendLine(b"You are alone in this room.")

    def register_password(self, password):
        self.character_creation_data['password'] = password
        self.x = 500 #Default starting x coordinate
        self.y = 500 #Default starting y coordinate
        self.in_zone = False #default to not in zone.
        self.sendLine(b"Confirm your password:")
        self.state = "CONFIRM_PASSWORD"
        
    def handle_command(self, command):
        try:
            process_command(self, command)
        except Exception as e:
            logging.error(f"Error while handling command '{command}' for {self.username}: {e}", exc_info=True)
            self.sendLine(b"An error occurred while processing your command.")

    def display_room(self):
        """Displays the grid map around the player."""
        try:
            map_view = UTILITIES["render_open_land"](
                self.x,
                self.y,
                world_map=WORLD_MAP,
                overlays=WORLD_OVERLAYS,
            )
            self.sendLine(map_view.encode("utf-8"))
        except KeyError:
            self.sendLine(b"Error: Map rendering function is unavailable.")
        except Exception as e:
            logging.error(f"Error rendering map: {e}", exc_info=True)
            self.sendLine(b"An error occurred while rendering the map.")
        
    def track_player(self):
        track_player(self, players_in_rooms)
        logging.info("Player %s is now at %s.", self.username, self.location_key)
    
    def untrack_player(self):
        room_key = self.location_key
        untrack_player(self, players_in_rooms)
        logging.info("Player %s left location %s.", self.username, room_key)

    @property
    def location_key(self):
        return coordinate_key(self.x, self.y)

    def confirm_password(self, password):
        if self.character_creation_data['password'] == password:
            hashed_password = hash_password(password)
            self.cursor.execute("""
                INSERT INTO players (username, password, x, y, is_admin) 
                VALUES (?, ?, ?, ?, ?)
            """, (self.username, hashed_password, self.x, self.y, self.is_admin))
            self.cursor.connection.commit()
            del self.character_creation_data['password']
            self.sendLine(b"Account created! Please choose your specialty:")
            self.sendLine(b"a) Ninjutsu\nb) Genjutsu\nc) Taijutsu")
            self.state = "CHOOSE_SPECIALTY"
        else:
            self.sendLine(b"Passwords do not match. Try again.")
            self.state = "REGISTER_PASSWORD"

    def choose_specialty(self, choice):
        specialties = {"a": "Ninjutsu", "b": "Genjutsu", "c": "Taijutsu"}
        if choice.lower() in specialties:
            self.character_creation_data['specialty'] = specialties[choice.lower()]
            self.cursor.execute("UPDATE players SET role_type=? WHERE username=?",
                                (choice.lower(), self.username))
            self.cursor.connection.commit()
            self.sendLine(f"Specialty {specialties[choice.lower()]} selected! Now allocate 10 points.".encode('utf-8'))
            self.character_creation_data['remaining_points'] = 10
            self.state = "ALLOCATE_STATS"
        else:
            self.sendLine(b"Invalid choice. Choose again: a) Ninjutsu, b) Genjutsu, c) Taijutsu")

    def allocate_stats(self, line):
        """Handles stat allocation."""
        try:
            parts = line.strip().split('=')
            if len(parts) != 2:
                self.sendLine(b"Invalid format. Use: stat_name=value (e.g., strength=3).")
                return
    
            stat, value = parts[0].strip().lower(), int(parts[1].strip())
            if stat not in ['strength', 'dexterity', 'agility', 'intelligence', 'wisdom']:
                self.sendLine(b"Invalid stat name.")
                return
    
            remaining = self.character_creation_data.get('remaining_points', 0)
            if value <= 0:
                self.sendLine(b"Allocation values must be greater than zero.")
                return
            if remaining < value:
                self.sendLine(f"Not enough points. You have {remaining} left.".encode('utf-8'))
                return
    
            self.character_creation_data[stat] = self.character_creation_data.get(stat, 0) + value
            self.character_creation_data['remaining_points'] -= value
    
            self.cursor.execute(f"UPDATE players SET {stat}=? WHERE username=?",
                                (self.character_creation_data[stat], self.username))
            self.cursor.connection.commit()
    
            if self.character_creation_data['remaining_points'] <= 0:
                self.sendLine(b"Character is ready! Entering the game...")
                self.state = "COMMAND"
                self.track_player()
                self.display_room()
            else:
                self.sendLine(f"{stat.capitalize()} set to {self.character_creation_data[stat]}. Remaining points: {self.character_creation_data['remaining_points']}".encode('utf-8'))
    
        except ValueError:
            self.sendLine(b"Invalid value. Please enter a number.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol(cursor)  # Pass the cursor here

import json

def load_config(config_file=DEFAULT_CONFIG_FILE):
    """Loads server configuration from a JSON file."""
    try:
        with open(config_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"Config file {config_file} not found. Using defaults.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing config file: {e}. Using defaults.")
        return {}


def initialize_server(config_file=DEFAULT_CONFIG_FILE):
    """Initializes all systems required for the MUD server."""
    logging.info("Initializing Ninja MUD Server...")

    # 1. Load Configuration
    config = load_config(config_file)

    # 2. Setup Logging
    configure_logging(config.get("log_file", "mud_debug.log"))
    logging.info("Logging initialized.")

    # 3. Initialize Database
    global conn, cursor, MOTD
    db_file = config.get("db_file", DEFAULT_DB_FILE)
    if conn:
        conn.close()
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    ensure_tables_exist(conn)
    apply_migrations(conn)
    logging.info(f"Database connection established using {db_file}.")
    
    # 4. Preload Map
    
#    WORLD_MAP = load_world_map()
#    logging.info(f"Map file loaded")

    # 5. Preload Zones
    zone_directory = config.get("zone_directory", "zones")
#    preload_zones(zone_directory)
    logging.info(f"Zone data preloaded from {zone_directory}.")

# Load utilities moved to first spot after defining due to timing issues. Lazy import wasn't working and I didn't want to get stopped by this problem with so much work to be done. Hopefully I'll come back and clean it up when I get further along.
    #6. Load Utilities
    #load_utilities()
    #logging.info(f"Utilities loaded: {len(UTILITIES)}")

    # 7. Load Commands
    COMMAND_REGISTRY.clear()
    load_commands()
    logging.info(f"Commands loaded: {len(COMMAND_REGISTRY)}")

    # 8. Load MOTD (Message of the Day)
    try:
        motd_file = config.get("motd_file", "motd.txt")
        with open(motd_file, "r") as file:
            MOTD = file.read().strip()
            logging.info(f"MOTD loaded from {motd_file}.")
    except FileNotFoundError:
        MOTD = DEFAULT_MOTD
        logging.warning("MOTD file not found. Using default message.")    

    # Final Validation
    validate_server_state(config)

    logging.info("Ninja MUD Server initialized successfully.")
    return config

def validate_server_state(config):
    """Performs validation checks to ensure server state is operational."""
    errors = []

    if not COMMAND_REGISTRY:
        errors.append("No commands loaded. Check command modules.")
    else:
        for cmd, handler in COMMAND_REGISTRY.items():
            if not callable(handler):
                errors.append(f"Command '{cmd}' is not callable. Check its handler.")
    
    if not UTILITIES:
        errors.append("No utilities loaded. Check utils module.")
    else:
        for name, func in UTILITIES.items():
            if name != "WORLD_MAP" and not callable(func):
                errors.append(f"Utility '{name}' is not callable. Check its definition.")

    if not WORLD_MAP or not WORLD_MAP[0]:
        errors.append("World map is empty.")

    if not os.path.isdir(config.get("zone_directory", "zones")):
        errors.append("Configured zone directory does not exist.")

    try:
        port = int(config.get("server_port", DEFAULT_PORT))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("Configured server_port must be an integer between 1 and 65535.")

    required_tables = {"players", "rooms", "schema_migrations"}
    tables = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    missing_tables = sorted(required_tables - tables)
    if missing_tables:
        errors.append(f"Database is missing tables: {', '.join(missing_tables)}.")

    if errors:
        for error in errors:
            logging.error(error)
        raise RuntimeError("Server validation failed.")

    logging.info("Server state validation passed.")
    return True


def run_server(config_file=DEFAULT_CONFIG_FILE, reactor_instance=reactor):
    """Initialize the MUD and listen on the configured TCP port."""
    config = initialize_server(config_file)
    port = int(config.get("server_port", DEFAULT_PORT))
    reactor_instance.listenTCP(port, NinjaMUDFactory())
    logging.info("Ninja MUD Server running on port %s.", port)
    reactor_instance.run()
    return config

if __name__ == "__main__":
    run_server()
