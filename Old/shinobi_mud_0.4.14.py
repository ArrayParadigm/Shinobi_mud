import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib
import logging
import json

# Import commands from various modules
from general_commands import COMMANDS as general_commands
from admin_commands import COMMANDS as admin_commands
from social_commands import COMMANDS as social_commands

# Combine commands into one registry
general_status_commands = {
    cmd: lambda *args, func=func: func(*args, cursor)
    for cmd, func in general_commands.items() if cmd == "status"
}
general_non_status_commands = {
    cmd: func
    for cmd, func in general_commands.items() if cmd != "status"
}
COMMAND_REGISTRY = {
    **general_status_commands,
    **general_non_status_commands,
    **admin_commands,
    **social_commands,
}

# Setup for enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mud_debug.log"),
        logging.StreamHandler()
    ]
)

# Database setup
conn = sqlite3.connect('mud_game_10_rooms.db')
cursor = conn.cursor()


def ensure_tables_exist():
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT NOT NULL,
            current_room INTEGER DEFAULT 1000,
            is_admin BOOLEAN DEFAULT 1,
            role_type INTEGER DEFAULT 0, -- default to Newbie
            health INTEGER DEFAULT 10,
            stamina INTEGER DEFAULT 10,
            chakra INTEGER DEFAULT 10,
            strength INTEGER DEFAULT 5,
            dexterity INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            wisdom INTEGER DEFAULT 5,
            dojo_alignment TEXT DEFAULT 'None'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            exits TEXT
        )''')
        cursor.execute('''INSERT OR IGNORE INTO rooms (id, name, description, exits) VALUES
            (1000, "Default Room", "This is the starting room.", "{}")''')
        conn.commit()
        logging.info("Database tables ensured.")
    except Exception as e:
        logging.error(f"Failed to ensure database tables: {e}")


ensure_tables_exist()
players_in_rooms = {}


class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.character_creation_data = {}  # Temporary storage for character creation
        self.username = None
        self.current_room = 1000
        self.is_admin = False

    def connectionMade(self):
        logging.info("New connection established from %s.", self.transport.getPeer())
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        command = line.decode('utf-8').strip()
        try:
            if self.state == "GET_USERNAME":
                self.handle_username(command)
            elif self.state == "GET_PASSWORD":
                self.handle_password(command)
            elif self.state == "REGISTER_PASSWORD":
                self.register_password(command)
            elif self.state == "CONFIRM_PASSWORD":
                self.confirm_password(command)
            elif self.state == "CHOOSE_SPECIALTY":
                self.choose_specialty(command)
            elif self.state == "ALLOCATE_STATS":
                self.allocate_stats(command)
            elif self.state == "COMMAND":
                self.handle_command(command)
            else:
                self.sendLine(b"Unknown state.")
        except Exception as e:
            logging.error(f"Error in state {self.state}: {e}", exc_info=True)
            self.sendLine(b"An error occurred. Please try again.")

    def handle_username(self, username):
        self.username = username
        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.current_room = player[3]
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
            self.sendLine(b"Login successful!")
            self.state = "COMMAND"
            self.track_player()
            self.display_room()
        else:
            self.sendLine(b"Incorrect password. Try again.")

    def register_password(self, password):
        self.character_creation_data['password'] = password
        self.sendLine(b"Confirm your password:")
        self.state = "CONFIRM_PASSWORD"
        
    def handle_command(self, command):
        """Handles user commands during gameplay."""
        parts = command.strip().split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
    
        handler = COMMAND_REGISTRY.get(cmd)
        if handler:
            logging.info(f"Executing command '{cmd}' for user {self.username} with args {args}.")
            handler(self, players_in_rooms, *args)
        else:
            logging.warning(f"Unknown command '{cmd}' received from {self.username}.")
            self.sendLine(b"Unknown command.")

    def display_room(self):
        """Displays current room details."""
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()
    
        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
            try:
                # Safely parse the exits using json.loads
                exits = json.loads(room[3])
                exits_list = ", ".join(exits.keys())
                self.sendLine(f"Exits: {exits_list}".encode('utf-8'))
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse exits for room {self.current_room}: {e}")
                self.sendLine(b"Exits: (none or error reading exits)")
            self.list_players_in_room()
        else:
            logging.error(f"Room with ID {self.current_room} not found for user {self.username}.")
            self.sendLine(b"Room not found.")
        
    def track_player(self):
        """Tracks the player's current room."""
        if self.current_room not in players_in_rooms:
            players_in_rooms[self.current_room] = []
        players_in_rooms[self.current_room].append(self)
        logging.info(f"Player {self.username} is now in room {self.current_room}.")
        
    def untrack_player(self):
        """Removes the player from the current room tracking."""
        if self.current_room in players_in_rooms:
            players_in_rooms[self.current_room].remove(self)
            logging.info(f"Player {self.username} left room {self.current_room}.")

    def confirm_password(self, password):
        if self.character_creation_data['password'] == password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO players (username, password, current_room, is_admin) 
                VALUES (?, ?, ?, ?)
            """, (self.username, hashed_password, self.current_room, self.is_admin))
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
        return NinjaMUDProtocol()


# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
