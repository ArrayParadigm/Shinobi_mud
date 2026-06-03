import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import logging
import importlib
import json
import inspect
import sys
from datetime import datetime
from auth import hash_password, validate_username, verify_password
from command_system import CommandSpec
from combat import clear_engagement, tick_combat
from content import sync_authored_content
from locations import broadcast_at, coordinate_key, is_within_bounds, nearby_players, online_players, players_at, track_player, untrack_player
from migrations import apply_migrations, create_players_table
from npcs import npc_locations, tick_npcs
from techniques import tick_jutsu_states
import presentation
from presentation import prompt
from twisted.internet import task

DEBUG_MODE = True  # True allows for debugging options; False disables them
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_DB_FILE = "shinobi_mud.db"
DEFAULT_MOTD = "Welcome to Ninja MUD!"
DEFAULT_PORT = 4000
DATABASE_BUSY_TIMEOUT_SECONDS = 1
DEFAULT_NEARBY_PLAYER_RADIUS = 20
DEFAULT_COLOR_ENABLED = True
DEFAULT_LOG_FILE = os.path.join(
    "logs",
    f"mud_{datetime.now():%Y%m%d_%H%M%S}_{os.getpid()}.log",
)

# Command modules import shinobi_mud. Reuse this module when launched as a script.
sys.modules.setdefault("shinobi_mud", sys.modules[__name__])

def configure_logging(log_file=DEFAULT_LOG_FILE):
    """Replace root logging handlers so repeated initialization stays clean."""
    log_directory = os.path.dirname(log_file)
    if log_directory:
        os.makedirs(log_directory, exist_ok=True)

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
COMMAND_ALIASES = {}
COMMAND_SHORTCUTS = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "l": "look",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}
UTILITIES = {}
players_in_rooms = {}
WORLD_OVERLAYS = {}
ACTIVE_CONFIG = {}
SHOW_NEARBY_PLAYERS = True
NEARBY_PLAYER_RADIUS = DEFAULT_NEARBY_PLAYER_RADIUS
WORLD_TICK_INTERVAL_SECONDS = 30
WORLD_TICK_LOOP = None
COMBAT_TICK_INTERVAL_SECONDS = 1
COMBAT_TICK_LOOP = None
NORMAL_MAP_WIDTH_RADIUS = 5
NORMAL_MAP_HEIGHT_RADIUS = 5
BASE_ATTRIBUTE_SCORE = 10
ATTRIBUTE_ALLOCATION_POINTS = 10
ATTRIBUTE_NAMES = ("strength", "dexterity", "agility", "intelligence", "wisdom")
SPECIALTIES = {
    "1": "Ninjutsu",
    "2": "Genjutsu",
    "3": "Taijutsu",
    "a": "Ninjutsu",
    "b": "Genjutsu",
    "c": "Taijutsu",
}
CLANS = {
    "1": "Unaffiliated",
    "2": "Leaf",
    "3": "Sand",
    "4": "Mist",
}
NATURAL_RELEASES = {
    "1": "Fire",
    "2": "Water",
    "3": "Earth",
    "4": "Lightning",
    "5": "Wind",
}

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
    COMMAND_REGISTRY.clear()
    COMMAND_ALIASES.clear()
    for module_name in COMMAND_MODULES:
        try:
            # Import the module
            module = importlib.import_module(module_name)
            # Check if the module defines a COMMANDS dictionary
            if hasattr(module, "COMMANDS"):
                for command_name, command in module.COMMANDS.items():
                    if command_name in COMMAND_REGISTRY or command_name in COMMAND_ALIASES:
                        raise RuntimeError(f"Duplicate command registration: {command_name}")
                    COMMAND_REGISTRY[command_name] = command
                    for alias in getattr(command, "aliases", ()):
                        if alias in COMMAND_REGISTRY or alias in COMMAND_ALIASES:
                            raise RuntimeError(f"Duplicate command alias registration: {alias}")
                        COMMAND_ALIASES[alias] = command_name
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
def connect_database(db_file):
    """Open a server database connection that fails quickly when writes are blocked."""
    connection = sqlite3.connect(db_file, timeout=DATABASE_BUSY_TIMEOUT_SECONDS)
    connection.row_factory = sqlite3.Row
    connection.execute(
        f"PRAGMA busy_timeout = {DATABASE_BUSY_TIMEOUT_SECONDS * 1000}"
    )
    return connection


conn = None
cursor = None
MOTD = DEFAULT_MOTD

def debug_log(message):
    """Wrapper for debug-level logging."""
    logging.debug(message)

def preload_zones(zone_directory, connection=None):
    """Preloads zone files from the specified directory and initializes database rooms."""
    active_connection = connection or conn
    if active_connection is None:
        raise RuntimeError("Database connection is not initialized.")
    active_cursor = active_connection.cursor()
    for file_name in os.listdir(zone_directory):
        if file_name.endswith(".json"):
            try:
                with open(os.path.join(zone_directory, file_name), "r") as file:
                    zone_data = json.load(file)
                    logging.info(f"Preloaded zone: {zone_data['name']}")

                    # Ensure rooms are loaded into the database
                    for room_id, room_data in zone_data["rooms"].items():
                        active_cursor.execute(
                            '''INSERT OR IGNORE INTO rooms (id, name, description, exits) 
                            VALUES (?, ?, ?, ?)''',
                            (
                                room_id,
                                room_data.get("name", "Unnamed Room"),
                                room_data.get("description", "No description."),
                                json.dumps(room_data.get("exits", {})),
                            )
                        )
                active_connection.commit()
            except Exception as e:
                logging.error(f"Error preloading zone file {file_name}: {e}", exc_info=True)


def resolve_command_name(command_name):
    """Resolve exact names, reserved shortcuts, and unambiguous command prefixes."""
    command_name = command_name.strip().lower()
    if not command_name:
        return None, []

    if command_name in COMMAND_REGISTRY:
        return command_name, []

    if command_name in COMMAND_ALIASES:
        return COMMAND_ALIASES[command_name], []

    shortcut = COMMAND_SHORTCUTS.get(command_name)
    if shortcut in COMMAND_REGISTRY:
        return shortcut, []

    matching_names = sorted(
        candidate
        for candidate in (*COMMAND_REGISTRY, *COMMAND_ALIASES)
        if candidate.startswith(command_name)
    )
    matching_commands = {
        COMMAND_ALIASES.get(candidate, candidate)
        for candidate in matching_names
    }
    if len(matching_commands) == 1:
        return matching_commands.pop(), []
    return None, matching_names


def process_command(player, command):
    command = command.strip()  # Strip any leading/trailing whitespace
    if not command:
        return
    
    # Split command into command and arguments
    parts = command.split(maxsplit=1)  # Split at the first whitespace boundary
    cmd = parts[0].lower()  # Extract and normalize command name
    raw_args = parts[1] if len(parts) > 1 else ""  # Extract raw argument string
    split_args = raw_args.split()  # Split arguments into a list
    
    # Use COMMAND_REGISTRY for all commands
    resolved_cmd, matches = resolve_command_name(cmd)
    command_spec = COMMAND_REGISTRY.get(resolved_cmd)
    if command_spec:
        logging.info("Executing command '%s' for player %s.", resolved_cmd, player.username)
        try:
            # Pass player, players_in_rooms, raw argument string, and split arguments
            command_spec(player, players_in_rooms, raw_args, split_args)
        except Exception as e:
            logging.error(f"Error executing command '{resolved_cmd}' for {player.username}: {e}", exc_info=True)
            player.sendLine(b"An error occurred while executing your command.")
    elif matches:
        player.sendLine(
            f"Ambiguous command '{cmd}': {', '.join(matches)}".encode("utf-8")
        )
        logging.info("Ambiguous command '%s' issued by player %s.", cmd, player.username)
    else:
        player.sendLine(f"Unknown command: {cmd}".encode('utf-8'))
        logging.warning(f"Unknown command '{cmd}' issued by player {player.username}")


def is_username_active(username, exclude=None):
    """Return True when a username is already attached to an active protocol."""
    return any(
        player is not exclude and getattr(player, "username", None) == username
        for room_players in players_in_rooms.values()
        for player in room_players
    )


def ensure_tables_exist(connection=None):
    active_connection = connection or conn
    if active_connection is None:
        raise RuntimeError("Database connection is not initialized.")
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
        "CHOOSE_CLAN": "choose_clan",
        "CHOOSE_RELEASE": "choose_release",
        "ALLOCATE_STATS": "allocate_stats",
        "COMMAND": "handle_command",
    }


def broadcast_global(message, exclude=None):
    """Send a server-wide message to every tracked online character."""
    seen = set()
    for bucket in players_in_rooms.values():
        for recipient in bucket:
            if id(recipient) in seen:
                continue
            seen.add(id(recipient))
            if recipient is not exclude and getattr(recipient, "username", None):
                recipient.sendLine(message.encode("utf-8"))


def active_session_for(username, exclude=None):
    """Return one tracked protocol for an already-online username."""
    target = username.casefold()
    seen = set()
    for bucket in players_in_rooms.values():
        for player in bucket:
            if id(player) in seen:
                continue
            seen.add(id(player))
            player_username = getattr(player, "username", None)
            if player is not exclude and player_username and player_username.casefold() == target:
                return player
    return None


class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self, cursor=None, connection=None, owns_connection=False):
        if cursor is not None and connection is not None:
            raise ValueError("Provide a database cursor or connection, not both.")
        self.connection = connection or (cursor.connection if cursor is not None else None)
        self.cursor = cursor or (self.connection.cursor() if self.connection is not None else None)
        self.owns_connection = owns_connection
        self.connection_closed = False
        self.state = "GET_USERNAME"
        self.character_creation_data = {}
        self.username = None
        self.is_admin = False
        self.is_builder = False
        self.player_class = 'newbie' # Default to a basic Class
        self.STATE_HANDLERS = get_state_handlers()
        
        self.in_zone = False
        self.x = 500
        self.y = 500
        self.color_enabled = bool(ACTIVE_CONFIG.get("default_color_enabled", DEFAULT_COLOR_ENABLED))
                
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
        if self.username and self.cursor:
            try:
                clear_engagement(self.cursor, self.username)
            except sqlite3.Error:
                logging.warning("Unable to clear combat engagement for %s.", self.username)
        self.untrack_player()
        if self.username:
            broadcast_global(f"{self.username} has disconnected.", exclude=self)
        self.close_connection()

    def close_connection(self):
        """Close a protocol-owned database connection once."""
        if self.owns_connection and self.connection is not None and not self.connection_closed:
            self.connection.close()
            self.connection_closed = True
    
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

        active_session = active_session_for(self.username, exclude=self)
        if active_session:
            active_session.sendLine(b"Another connection has taken over this character.")
            active_session.untrack_player()
            if getattr(active_session, "transport", None):
                active_session.transport.loseConnection()
            active_session.close_connection()
            active_session.username = None
            active_session.state = "DISCONNECTED"

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
        self.is_builder = bool(player["is_builder"])
        self.player_class = player["role_type"]
        self.sendLine(b"Login successful!")
        self.state = "COMMAND"
        self.track_player()
        broadcast_global(f"{self.username} has connected.", exclude=self)
        self.display_room()
        self.display_prompt()
            
    def list_players_in_room(self):
        """List other players at the current world coordinate."""
        others = [player.username for player in players_at(players_in_rooms, self.x, self.y, self)]
        logging.info("User %s checking location %s. Others here: %s", self.username, self.location_key, others)
        
        if others:
            self.sendLine(f"Also here: {', '.join(others)}".encode('utf-8'))

    def list_nearby_players(self):
        """List characters in the configured nearby grid radius."""
        if not SHOW_NEARBY_PLAYERS:
            return

        nearby = nearby_players(
            players_in_rooms,
            self.x,
            self.y,
            NEARBY_PLAYER_RADIUS,
            exclude=self,
        )
        if nearby:
            player_list = ", ".join(
                f"{player.username} ({player.x}, {player.y}; {distance} away)"
                for distance, player in nearby
            )
            self.sendLine(f"Nearby: {player_list}".encode("utf-8"))

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
        finally:
            self.display_prompt()

    def display_room(self):
        """Displays the grid map around the player."""
        try:
            UTILITIES["render_room"](self, WORLD_OVERLAYS)
            map_view = UTILITIES["render_open_land"](
                self.x,
                self.y,
                world_map=WORLD_MAP,
                overlays=WORLD_OVERLAYS,
                width_radius=NORMAL_MAP_WIDTH_RADIUS,
                height_radius=NORMAL_MAP_HEIGHT_RADIUS,
                color_enabled=self.color_enabled,
                player_locations=self._visible_player_locations(NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
                npc_locations=npc_locations(self.cursor, self.x, self.y, NORMAL_MAP_WIDTH_RADIUS, NORMAL_MAP_HEIGHT_RADIUS),
            )
            self.sendLine(map_view.encode("utf-8"))
            self.sendLine(presentation.divider("Nearby", self.color_enabled).encode("utf-8"))
            self.list_players_in_room()
            self.list_nearby_players()
        except KeyError:
            self.sendLine(b"Error: Map rendering function is unavailable.")
        except Exception as e:
            logging.error(f"Error rendering map: {e}", exc_info=True)
            self.sendLine(b"An error occurred while rendering the map.")

    def _visible_player_locations(self, width_radius, height_radius):
        locations = set()
        for other_player in online_players(players_in_rooms):
            if other_player is self:
                continue
            if abs(other_player.x - self.x) <= width_radius and abs(other_player.y - self.y) <= height_radius:
                locations.add((other_player.x, other_player.y))
        return locations
        
    def track_player(self):
        broadcast_at(
            players_in_rooms,
            self.location_key,
            f"{self.username} has arrived.",
            exclude=self,
        )
        track_player(self, players_in_rooms)
        logging.info("Player %s is now at %s.", self.username, self.location_key)
    
    def untrack_player(self):
        if self.username is None:
            return
        room_key = self.location_key
        if self not in players_in_rooms.get(room_key, []):
            return
        broadcast_at(
            players_in_rooms,
            room_key,
            f"{self.username} has left.",
            exclude=self,
        )
        untrack_player(self, players_in_rooms)
        logging.info("Player %s left location %s.", self.username, room_key)

    @property
    def location_key(self):
        return coordinate_key(self.x, self.y)

    def display_prompt(self):
        """Display a compact command prompt with current resources and location."""
        try:
            self.cursor.execute(
                """
                SELECT health, max_health, stamina, max_stamina, chakra, max_chakra
                FROM players
                WHERE username=?
                """,
                (self.username,),
            )
            stats = self.cursor.fetchone()
            if not stats:
                return

            overlay = WORLD_OVERLAYS.get(self.location_key)
            if overlay:
                location = f"{overlay['zone_name']} [{overlay['vnum']}] ({self.x}, {self.y})"
            else:
                location = f"({self.x}, {self.y})"
            self.sendLine(
                prompt(
                    stats["health"],
                    stats["max_health"],
                    stats["stamina"],
                    stats["max_stamina"],
                    stats["chakra"],
                    stats["max_chakra"],
                    location,
                    enabled=self.color_enabled,
                ).encode("utf-8")
            )
        except Exception as exc:
            logging.error("Unable to display prompt for %s: %s", self.username, exc, exc_info=True)

    def confirm_password(self, password):
        if self.character_creation_data['password'] == password:
            hashed_password = hash_password(password)
            self.cursor.execute("""
                INSERT INTO players (
                    username, password, x, y, is_admin, is_builder,
                    strength, dexterity, agility, intelligence, wisdom
                )
                VALUES (?, ?, ?, ?, ?, ?, 10, 10, 10, 10, 10)
            """, (self.username, hashed_password, self.x, self.y, self.is_admin, self.is_builder))
            self.cursor.connection.commit()
            del self.character_creation_data['password']
            self.sendLine(b"Account created. Default character stats are set to 10.")
            self.sendLine(b"Character is ready! Entering the game...")
            self.state = "COMMAND"
            self.track_player()
            broadcast_global(f"{self.username} has connected.", exclude=self)
            self.display_room()
            self.display_prompt()
        else:
            self.sendLine(b"Passwords do not match. Try again.")
            self.state = "REGISTER_PASSWORD"

    def choose_specialty(self, choice):
        specialty = SPECIALTIES.get(choice.strip().lower())
        if specialty:
            self.character_creation_data["specialty"] = specialty
            self.cursor.execute(
                "UPDATE players SET role_type=? WHERE username=?",
                (specialty, self.username),
            )
            self.cursor.connection.commit()
            self.sendLine(f"Specialty selected: {specialty}.".encode("utf-8"))
            self.sendLine(b"Choose a clan: 1) Unaffiliated  2) Leaf  3) Sand  4) Mist")
            self.state = "CHOOSE_CLAN"
        else:
            self.sendLine(b"Choose a specialty: 1) Ninjutsu  2) Genjutsu  3) Taijutsu")

    def choose_clan(self, choice):
        """Persist the initial clan selection without attaching bonuses yet."""
        clan = CLANS.get(choice.strip().lower())
        if not clan:
            self.sendLine(b"Choose a clan: 1) Unaffiliated  2) Leaf  3) Sand  4) Mist")
            return
        self.character_creation_data["clan"] = clan
        self.cursor.execute(
            "UPDATE players SET clan=? WHERE username=?",
            (clan, self.username),
        )
        self.cursor.connection.commit()
        self.sendLine(f"Clan selected: {clan}.".encode("utf-8"))
        self.sendLine(b"Choose a natural release: 1) Fire  2) Water  3) Earth  4) Lightning  5) Wind")
        self.state = "CHOOSE_RELEASE"

    def choose_release(self, choice):
        """Persist the character's initial chakra nature."""
        natural_release = NATURAL_RELEASES.get(choice.strip().lower())
        if not natural_release:
            self.sendLine(b"Choose a natural release: 1) Fire  2) Water  3) Earth  4) Lightning  5) Wind")
            return
        self.character_creation_data["natural_release"] = natural_release
        self.cursor.execute(
            "UPDATE players SET natural_release=? WHERE username=?",
            (natural_release, self.username),
        )
        self.cursor.connection.commit()
        self.sendLine(f"Natural release selected: {natural_release}.".encode("utf-8"))
        self.sendLine(
            (
                "Distribute 10 bonus points in one line. "
                "Example: strength=2 dexterity=2 agility=2 intelligence=2 wisdom=2"
            ).encode("utf-8")
        )
        self.state = "ALLOCATE_STATS"

    def allocate_stats(self, line):
        """Apply one complete, readable allocation of attribute bonuses."""
        try:
            allocations = {}
            for assignment in line.replace(",", " ").split():
                stat, value = assignment.split("=", 1)
                stat = stat.strip().lower()
                if stat not in ATTRIBUTE_NAMES or stat in allocations:
                    raise ValueError
                allocations[stat] = int(value)
            if set(allocations) != set(ATTRIBUTE_NAMES):
                raise ValueError
            if any(value < 0 for value in allocations.values()):
                self.sendLine(b"Allocation values cannot be negative.")
                return
            if sum(allocations.values()) != ATTRIBUTE_ALLOCATION_POINTS:
                self.sendLine(b"Your five bonus allocations must total exactly 10 points.")
                return

            final_stats = {
                stat: BASE_ATTRIBUTE_SCORE + allocations[stat]
                for stat in ATTRIBUTE_NAMES
            }
            self.cursor.execute(
                """
                UPDATE players
                SET strength=?, dexterity=?, agility=?, intelligence=?, wisdom=?
                WHERE username=?
                """,
                (*[final_stats[stat] for stat in ATTRIBUTE_NAMES], self.username),
            )
            self.cursor.connection.commit()
            self.sendLine(
                (
                    "Attributes set: "
                    + ", ".join(f"{stat}={final_stats[stat]}" for stat in ATTRIBUTE_NAMES)
                    + "."
                ).encode("utf-8")
            )
            self.sendLine(b"Character is ready! Entering the game...")
            self.state = "COMMAND"
            self.track_player()
            self.display_room()
            self.display_prompt()
        except (ValueError, TypeError):
            self.sendLine(
                (
                    "Use all five stats in one line, totaling 10 bonus points: "
                    "strength=2 dexterity=2 agility=2 intelligence=2 wisdom=2"
                ).encode("utf-8")
            )

class NinjaMUDFactory(protocol.Factory):
    def __init__(self, db_file):
        self.db_file = db_file

    def buildProtocol(self, addr):
        return NinjaMUDProtocol(
            connection=connect_database(self.db_file),
            owns_connection=True,
        )

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
    ACTIVE_CONFIG.clear()
    ACTIVE_CONFIG.update(config)

    # 2. Setup Logging
    configure_logging(config.get("log_file", DEFAULT_LOG_FILE))
    logging.info("Logging initialized.")

    # 3. Initialize Database
    global conn, cursor, MOTD, SHOW_NEARBY_PLAYERS, NEARBY_PLAYER_RADIUS
    db_file = config.get("db_file", DEFAULT_DB_FILE)
    if conn:
        conn.close()
    conn = connect_database(db_file)
    cursor = conn.cursor()
    ensure_tables_exist(conn)
    apply_migrations(conn)
    logging.info(f"Database connection established using {db_file}.")
    
    # 4. Preload Map
    
#    WORLD_MAP = load_world_map()
#    logging.info(f"Map file loaded")

    # 5. Preload Zones
    zone_directory = config.get("zone_directory", "zones")
    UTILITIES["preload_zones_with_anchors"](WORLD_OVERLAYS, zone_directory)
    logging.info(
        "Zone data preloaded from %s with %s overlay rooms.",
        zone_directory,
        len(WORLD_OVERLAYS),
    )
    imported_content = sync_authored_content(conn, zone_directory, WORLD_OVERLAYS)
    logging.info(
        "Authored content synchronized: %s item spawns and %s NPC spawns created.",
        imported_content["item_spawns"],
        imported_content["npc_spawns"],
    )

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
    SHOW_NEARBY_PLAYERS = config.get("show_nearby_players", True)
    NEARBY_PLAYER_RADIUS = int(
        config.get("nearby_player_radius", DEFAULT_NEARBY_PLAYER_RADIUS)
    )

    logging.info("Ninja MUD Server initialized successfully.")
    return config

def validate_server_state(config):
    """Performs validation checks to ensure server state is operational."""
    errors = []

    if not COMMAND_REGISTRY:
        errors.append("No commands loaded. Check command modules.")
    else:
        for cmd, command in COMMAND_REGISTRY.items():
            if not isinstance(command, CommandSpec):
                errors.append(f"Command '{cmd}' is missing metadata.")
            elif not callable(command):
                errors.append(f"Command '{cmd}' is not callable. Check its handler.")
            elif command.permission not in {"player", "builder", "admin"}:
                errors.append(f"Command '{cmd}' has an invalid permission level.")
            elif not command.usage or not command.description:
                errors.append(f"Command '{cmd}' has incomplete help metadata.")
    
    if not UTILITIES:
        errors.append("No utilities loaded. Check utils module.")
    else:
        for name, func in UTILITIES.items():
            if name != "WORLD_MAP" and not callable(func):
                errors.append(f"Utility '{name}' is not callable. Check its definition.")

    if not WORLD_MAP or not WORLD_MAP[0]:
        errors.append("World map is empty.")

    invalid_overlays = sorted(
        coordinates
        for coordinates in WORLD_OVERLAYS
        if not is_within_bounds(WORLD_MAP, *coordinates)
    )
    if invalid_overlays:
        errors.append(f"Zone overlays fall outside the world map: {invalid_overlays}.")

    if not os.path.isdir(config.get("zone_directory", "zones")):
        errors.append("Configured zone directory does not exist.")

    try:
        port = int(config.get("server_port", DEFAULT_PORT))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("Configured server_port must be an integer between 1 and 65535.")

    show_nearby_players = config.get("show_nearby_players", True)
    if not isinstance(show_nearby_players, bool):
        errors.append("Configured show_nearby_players must be true or false.")

    default_color_enabled = config.get("default_color_enabled", DEFAULT_COLOR_ENABLED)
    if not isinstance(default_color_enabled, bool):
        errors.append("Configured default_color_enabled must be true or false.")

    try:
        nearby_player_radius = config.get(
            "nearby_player_radius",
            DEFAULT_NEARBY_PLAYER_RADIUS,
        )
        if isinstance(nearby_player_radius, bool) or int(nearby_player_radius) < 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("Configured nearby_player_radius must be a non-negative integer.")

    required_tables = {
        "players",
        "rooms",
        "schema_migrations",
        "item_definitions",
        "room_items",
        "character_inventory",
        "authored_content_seeds",
        "npc_templates",
        "npc_instances",
        "skill_definitions",
        "jutsu_definitions",
        "character_skills",
        "character_jutsus",
        "stance_definitions",
        "character_stances",
        "combat_engagements",
        "combat_action_queue",
    }
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
    try:
        config = initialize_server(config_file)
        port = int(config.get("server_port", DEFAULT_PORT))
        reactor_instance.listenTCP(port, NinjaMUDFactory(config.get("db_file", DEFAULT_DB_FILE)))
        logging.info("Ninja MUD Server running on port %s.", port)
        if hasattr(reactor_instance, "callLater"):
            start_world_tick(reactor_instance)
            start_combat_tick(reactor_instance)
        reactor_instance.run()
        return config
    except Exception:
        logging.exception("Unexpected server failure.")
        raise


def run_world_tick():
    """Advance lightweight persistent NPC bookkeeping."""
    if conn is None:
        raise RuntimeError("Database connection is not initialized.")
    updated_npcs = tick_npcs(conn)
    updated_jutsu_states = tick_jutsu_states(conn)
    logging.debug("World tick updated %s NPC instances.", updated_npcs)
    logging.debug("World tick expired %s jutsu states.", updated_jutsu_states)
    return updated_npcs


def start_world_tick(clock=reactor):
    """Start the minimal recurring world update loop."""
    global WORLD_TICK_LOOP
    if WORLD_TICK_LOOP and WORLD_TICK_LOOP.running:
        return WORLD_TICK_LOOP

    WORLD_TICK_LOOP = task.LoopingCall(run_world_tick)
    WORLD_TICK_LOOP.clock = clock
    WORLD_TICK_LOOP.start(WORLD_TICK_INTERVAL_SECONDS, now=False)
    logging.info("World tick scheduled every %s seconds.", WORLD_TICK_INTERVAL_SECONDS)
    return WORLD_TICK_LOOP


def run_combat_tick():
    """Resolve due combat pulses for connected characters and deliver feedback."""
    if conn is None:
        raise RuntimeError("Database connection is not initialized.")
    online = {
        player.username: player
        for bucket in players_in_rooms.values()
        for player in bucket
        if player.username
    }
    events = tick_combat(conn, online)
    for event in events:
        player = online.get(event["username"])
        if not player:
            continue
        for message, room_message in _combat_event_messages(event):
            player.sendLine(message.encode("utf-8"))
            if room_message:
                broadcast_at(
                    players_in_rooms,
                    coordinate_key(player.x, player.y),
                    room_message,
                    exclude=player,
                )
    return events


def start_combat_tick(clock=reactor):
    """Start the recurring combat-pulse delivery loop."""
    global COMBAT_TICK_LOOP
    if COMBAT_TICK_LOOP and COMBAT_TICK_LOOP.running:
        return COMBAT_TICK_LOOP

    COMBAT_TICK_LOOP = task.LoopingCall(run_combat_tick)
    COMBAT_TICK_LOOP.clock = clock
    COMBAT_TICK_LOOP.start(COMBAT_TICK_INTERVAL_SECONDS, now=False)
    logging.info("Combat tick scheduled every %s second.", COMBAT_TICK_INTERVAL_SECONDS)
    return COMBAT_TICK_LOOP


def _combat_event_messages(event):
    """Return player and local-room message pairs for one resolved pulse."""
    username = event["username"]
    npc_name = event["npc_name"]
    if event["status"] == "out_of_range":
        return [
            (
                f"{npc_name} is {event['distance']} step(s) away; your basic auto attack cannot connect.",
                None,
            )
        ]
    if event["status"] == "ended":
        return [(f"Your engagement with {npc_name} ends.", None)]
    messages = []
    if event["status"] == "npc_defeated":
        return [
            (
                f"You strike {npc_name} for {event['player_damage']} damage and defeat it.",
                f"{username} strikes {npc_name} for {event['player_damage']} damage and defeats it.",
            )
        ]
    if event["player_hit"]:
        messages.append(
            (
                f"You strike {npc_name} for {event['player_damage']} damage. {npc_name} has {event['npc_health']} health remaining.",
                f"{username} strikes {npc_name} for {event['player_damage']} damage. {npc_name} has {event['npc_health']} health remaining.",
            )
        )
    else:
        messages.append(
            (
                f"You attack {npc_name}, but miss.",
                f"{username} attacks {npc_name}, but misses.",
            )
        )
    if event["distance"] > 0:
        return messages
    if event["substitution"]:
        messages.append(
            (
                f"You evade {npc_name} through Substitution Technique. Jutsu: {event['substitution']['proficiency']} ({event['substitution']['progress_percent']}%).",
                f"{username} evades {npc_name} through Substitution Technique.",
            )
        )
    elif not event["npc_hit"]:
        messages.append(
            (
                f"{npc_name} attacks you, but misses.",
                f"{npc_name} attacks {username}, but misses.",
            )
        )
    elif event["player_defeated"]:
        messages.append(
            (
                f"{npc_name} strikes you for {event['npc_damage']} damage. You are defeated, then recover here with {event['player_health']} health.",
                f"{npc_name} strikes {username} for {event['npc_damage']} damage. {username} is defeated and recovers here.",
            )
        )
    else:
        messages.append(
            (
                f"{npc_name} strikes you for {event['npc_damage']} damage. You have {event['player_health']} health remaining.",
                f"{npc_name} strikes {username} for {event['npc_damage']} damage. {username} has {event['player_health']} health remaining.",
            )
        )
    return messages

if __name__ == "__main__":
    run_server()
