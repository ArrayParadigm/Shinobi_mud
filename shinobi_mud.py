import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib
import logging
import importlib
import json
import inspect

DEBUG_MODE = True  # True allows for debugging options; False disables them

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mud_debug.log"),
        logging.StreamHandler()
    ]
)

COMMAND_REGISTRY = {}
UTILITIES = {}
players_in_rooms = {}

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

# Setup for enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mud_debug.log"),
        logging.StreamHandler()
    ]
)

# Database setup
conn = sqlite3.connect('mud_game_10_rooms.db')
cursor = conn.cursor()

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


def ensure_tables_exist():
    try:
        # Create players table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT NOT NULL,
                x INTEGER DEFAULT 500,
                y INTEGER DEFAULT 500,
                is_admin BOOLEAN DEFAULT 1,
                role_type INTEGER DEFAULT 0,
                health INTEGER DEFAULT 10,
                stamina INTEGER DEFAULT 10,
                chakra INTEGER DEFAULT 10,
                strength INTEGER DEFAULT 5,
                dexterity INTEGER DEFAULT 5,
                agility INTEGER DEFAULT 5,
                intelligence INTEGER DEFAULT 5,
                wisdom INTEGER DEFAULT 5,
                dojo_alignment TEXT DEFAULT 'None'
            )
        ''')

        debug_log("Creating player due to lack of existence.")

        # Create rooms table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            exits TEXT
        )''')

        conn.commit()
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
#        self.current_room = None
        self.is_admin = True
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
#        self.current_room = 3000   # Assign a default VNUM room
        
    def connectionLost(self, reason):
        logging.info(f"Connection lost for user {self.username}. Reason: {reason}")
        self.untrack_player()
    
    def lineReceived(self, line):
        try:
            command = line.decode('utf-8').strip()  # Decode input and remove leading/trailing whitespace
            logging.info(f"Received command: {command} in state: {self.state}")
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
        self.username = username
        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
#            self.current_room = player[3]
            self.x = player[3]  # Assuming x is the 4th column
            self.y = player[4]  # Assuming x is the 5th column
            self.is_admin = bool(player[4])
            self.sendLine(b"Welcome back! Please enter your password:")
            self.state = "GET_PASSWORD"
        else:
            self.sendLine(b"Username not found. Creating a new account.")
            self.sendLine(b"Choose a password:")
            self.state = "REGISTER_PASSWORD"

    def handle_password(self, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM players WHERE username=? AND password=?", (self.username, hashed_password))
        player = cursor.fetchone()

        if player:
#            self.current_room = player[3]  # Load the last saved room from the database
            self.x = 1 
            self.y = 1
            self.is_admin = bool(player[3])
            self.player_class = player[5]
            self.sendLine(b"Login successful!")
            self.state = "COMMAND"
            self.track_player()
            self.display_room()
        else:
            self.sendLine(b"Incorrect password. Try again.")
            
    def list_players_in_room(self):
        """Lists other players in the current room."""
        others = [p.username for p in players_in_rooms.get(self.x, self.y, []) if p != self]
        logging.info(f"User {self.username} checking room {self.x, self.y}. Others here: {others}")
        
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
            map_view = UTILITIES["render_open_land"](self.x, self.y, world_map=WORLD_MAP)
            self.sendLine(map_view.encode("utf-8"))
        except KeyError:
            self.sendLine(b"Error: Map rendering function is unavailable.")
        except Exception as e:
            logging.error(f"Error rendering map: {e}", exc_info=True)
            self.sendLine(b"An error occurred while rendering the map.")
        
    def track_player(self):
        room_key = self.x, self.y
        if room_key not in players_in_rooms:
            players_in_rooms[room_key] = []  # Initialize the room with an empty list
        if self not in players_in_rooms[room_key]:  # Add the player object
            players_in_rooms[room_key].append(self)
        logging.info(f"Player {self.username} is now in room {self.x, self.y}.")
    
    def untrack_player(self):
        room_key = self.x, self.y
        if room_key in players_in_rooms and self in players_in_rooms[room_key]:
            players_in_rooms[room_key].remove(self)  # Remove the player object
            if not players_in_rooms[room_key]:  # If the room is empty, clean up
                del players_in_rooms[room_key]
        logging.info(f"Player {self.username} left room {room_key}.")

    def confirm_password(self, password):
        if self.character_creation_data['password'] == password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO players (username, password, x, y, is_admin) 
                VALUES (?, ?, ?, ?, ?)
            """, (self.username, hashed_password, self.x, self.y, self.is_admin))
            conn.commit()
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
            cursor.execute("UPDATE players SET role_type=? WHERE username=?", 
                           (choice.lower(), self.username))
            conn.commit()
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
            if remaining < value:
                self.sendLine(f"Not enough points. You have {remaining} left.".encode('utf-8'))
                return
    
            self.character_creation_data[stat] = self.character_creation_data.get(stat, 0) + value
            self.character_creation_data['remaining_points'] -= value
    
            cursor.execute(f"UPDATE players SET {stat}=? WHERE username=?", 
                           (self.character_creation_data[stat], self.username))
            conn.commit()
    
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

def load_config(config_file="config.json"):
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


def initialize_server():
    """Initializes all systems required for the MUD server."""
    logging.info("Initializing Ninja MUD Server...")

    # 1. Load Configuration
    config = load_config()

    # 2. Setup Logging
    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(config.get("log_file", "mud_debug.log")),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging initialized.")

    # 3. Initialize Database
    global conn, cursor
    db_file = config.get("db_file", "mud_game_10_rooms.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    ensure_tables_exist()
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
    load_commands()
    logging.info(f"Commands loaded: {len(COMMAND_REGISTRY)}")

    # 8. Load MOTD (Message of the Day)
    try:
        motd_file = config.get("motd_file", "motd.txt")
        with open(motd_file, "r") as file:
            global MOTD
            MOTD = file.read().strip()
            logging.info(f"MOTD loaded from {motd_file}.")
    except FileNotFoundError:
        MOTD = "Welcome to Ninja MUD!"
        logging.warning("MOTD file not found. Using default message.")    

    # Final Validation
    validate_server_state()

    logging.info("Ninja MUD Server initialized successfully.")

def validate_server_state():
    """Performs validation checks to ensure server state is operational."""
    if not COMMAND_REGISTRY:
        logging.error("No commands loaded. Check command modules.")
    else:
        for cmd, handler in COMMAND_REGISTRY.items():
            if not callable(handler):
                logging.error(f"Command '{cmd}' is not callable. Check its handler.")
    
    if not UTILITIES:
        logging.error("No utilities loaded. Check utils module.")
    else:
        for name, func in UTILITIES.items():
            if not callable(func):
                logging.error(f"Utility '{name}' is not callable. Check its definition.")

if __name__ == "__main__":
    initialize_server()

    # Start the reactor
    reactor.listenTCP(4000, NinjaMUDFactory())
    logging.info("Ninja MUD Server running on port 4000.")
    reactor.run()
