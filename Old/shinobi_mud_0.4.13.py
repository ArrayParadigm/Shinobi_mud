import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib
import logging

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

    # Ensure default room exists
    cursor.execute('''INSERT OR IGNORE INTO rooms (id, name, description, exits) VALUES
        (1000, "Default Room", "This is the starting room.", "{}")''')
    conn.commit()


ensure_tables_exist()
players_in_rooms = {}


class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.character_creation_data = {}  # Temporary storage for new player data during creation
        self.username = None
        self.current_room = 1000
        self.is_admin = False

    def connectionMade(self):
        logging.info("New connection established from %s.", self.transport.getPeer())
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        command = line.decode('utf-8').strip()
        logging.debug(f"Received input: {line}")
        try:
            if self.state == "GET_USERNAME":
                self.handle_username(line)
            elif self.state == "GET_PASSWORD":
                self.handle_password(line)
            elif self.state == "REGISTER_PASSWORD":
                self.register_password(line)
            elif self.state == "COMMAND":
                self.handle_command(line)
            elif self.state == "CONFIRM_PASSWORD":
                self.confirm_password(line)
            elif self.state == "CHOOSE_SPECIALTY":
                self.choose_specialty(line)
            elif self.state == "ALLOCATE_STATS":
                self.allocate_stats(line)
            else:
                self.sendLine(b"Unknown state.")
        except Exception as e:
            logging.error(f"Error processing input {line}: {e}", exc_info=True)
            self.sendLine(b"An error occurred. Please try again.")

    def handle_username(self, line):
        username = line.decode('utf-8').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.current_room = player[3]
            self.is_admin = bool(player[4])
            self.sendLine(b"Welcome back, %s! Please enter your password:" % username.encode('utf-8'))
            self.state = "GET_PASSWORD"
            logging.info(f"User {username} logged in.")
        else:
            self.sendLine(b"Username not found. Creating a new account.")
            self.sendLine(b"Choose a password:")
            self.state = "REGISTER_PASSWORD"
            logging.info(f"New user {username} is registering.")

    def handle_password(self, line):
        password = line.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("SELECT * FROM players WHERE username=? AND password=?", (self.username, hashed_password))
        player = cursor.fetchone()

        if player:
            self.sendLine(b"Login successful!")
            self.state = "COMMAND"
            self.track_player()
            self.display_room()
            logging.info(f"User {self.username} successfully logged in.")
        else:
            self.sendLine(b"Incorrect password.")
            logging.warning(f"User {self.username} entered an incorrect password.")

    def register_password(self, line):
        password = line.decode('utf-8').strip()
        self.character_creation_data['password'] = password
        self.sendLine(b"Confirm your password:")
        self.state = "CONFIRM_PASSWORD"

    def confirm_password(self, line):
        if self.character_creation_data['password'] != line.decode('utf-8').strip():
            self.sendLine(b"Passwords do not match. Try again.")
            self.state = "REGISTER_PASSWORD"
        else:
            hashed_password = hashlib.sha256(self.character_creation_data['password'].encode()).hexdigest()
            cursor.execute("INSERT INTO players (username, password, current_room, is_admin) VALUES (?, ?, ?, ?)",
                           (self.username, hashed_password, self.current_room, self.is_admin))
            conn.commit()
            self.sendLine(b"Account created successfully! What is your specialty?")
            self.sendLine(b"a) Ninjutsu\nb) Genjutsu\nc) Taijutsu")
            self.state = "CHOOSE_SPECIALTY"

    def choose_specialty(self, line):
        specialty_map = {"a": "Ninjutsu", "b": "Genjutsu", "c": "Taijutsu"}
        choice = line.decode('utf-8').strip().lower()
        if choice not in specialty_map:
            self.sendLine(b"Invalid choice. Choose again: a) Ninjutsu b) Genjutsu c) Taijutsu")
            return
        self.character_creation_data['specialty'] = specialty_map[choice]
        self.sendLine(f"Specialty {specialty_map[choice]} selected! Now allocate your stats (10 points).".encode('utf-8'))
        self.state = "ALLOCATE_STATS"
        self.character_creation_data['remaining_points'] = 10

    def allocate_stats(self, line):
        self.sendLine(b"Stat allocation not implemented in this demo. (For future logic).")
        self.state = "COMMAND"

    def handle_command(self, command):
        parts = command.strip().split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        handler = COMMAND_REGISTRY.get(cmd)
        if handler:
            logging.info(f"Executing command {cmd} for user {self.username} with args {args}.")
            handler(self, players_in_rooms, *args)
        else:
            logging.warning(f"Unknown command {cmd} received from {self.username}.")
            self.sendLine(b"Unknown command.")

    def track_player(self):
        if self.current_room not in players_in_rooms:
            players_in_rooms[self.current_room] = []
        players_in_rooms[self.current_room].append(self)
        logging.debug(f"Player {self.username} is now tracked in room {self.current_room}.")

    def untrack_player(self):
        if self.current_room in players_in_rooms:
            players_in_rooms[self.current_room].remove(self)
        logging.debug(f"Player {self.username} is no longer tracked in room {self.current_room}.")

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
            exits = ", ".join(eval(room[3]).keys())
            self.sendLine(f"Exits: {exits}".encode('utf-8'))
            self.list_players_in_room()
            logging.debug(f"Room displayed for {self.username}: {room[1]}")
        else:
            logging.error(f"Room with ID {self.current_room} not found for user {self.username}.")
            self.sendLine(b"Room not found.")

    def list_players_in_room(self):
        others = [p.username for p in players_in_rooms.get(self.current_room, []) if p != self]
        if others:
            self.sendLine(f"Also here: {', '.join(others)}".encode('utf-8'))
            logging.debug(f"Players in the same room as {self.username}: {', '.join(others)}")


class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()


# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
