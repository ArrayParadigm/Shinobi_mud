
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
COMMAND_REGISTRY = {**general_commands, **admin_commands, **social_commands}

# Setup for enhanced logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("mud_debug.log"),
                        logging.StreamHandler()
                    ])

# Database setup
conn = sqlite3.connect('mud_game_10_rooms.db')
cursor = conn.cursor()

def ensure_tables_exist():
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT NOT NULL,
                        current_room INTEGER DEFAULT 1000,
                        is_admin BOOLEAN DEFAULT 0
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        description TEXT,
                        exits TEXT
                    )''')

ensure_tables_exist()

players_in_rooms = {}

class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None
        self.current_room = 1000
        self.is_admin = False

    def connectionMade(self):
        logging.info("New connection established from %s.", self.transport.getPeer())
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        logging.debug(f"Received input: {line}")
        try:
            if self.state == "GET_USERNAME":
                self.handle_username(line)
            elif self.state == "GET_PASSWORD":
                self.handle_password(line)
            elif self.state == "REGISTER_PASSWORD":
                self.register_password(line)
            else:
                self.handle_command(line)
        except Exception as e:
            logging.error(f"Error processing input {line}: {e}", exc_info=True)
            self.sendLine(b"An error occurred. Please try again.")

    def handle_username(self, username):
        username = username.decode('utf-8').strip()
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

    def handle_password(self, password):
        password = password.decode('utf-8').strip()
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

    def register_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO players (username, password, current_room, is_admin) VALUES (?, ?, ?, ?)", 
                       (self.username, hashed_password, self.current_room, self.is_admin))
        conn.commit()

        self.sendLine(b"Account created successfully!")
        self.state = "COMMAND"
        self.track_player()
        self.display_room()
        logging.info(f"User {self.username} registered successfully.")

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

    def handle_command(self, command):
        parts = command.decode('utf-8').strip().split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        handler = COMMAND_REGISTRY.get(cmd)
        if handler:
            logging.info(f"Executing command {cmd} for user {self.username} with args {args}.")
            handler(self, players_in_rooms, *args)
        else:
            logging.warning(f"Unknown command {cmd} received from {self.username}.")
            self.sendLine(b"Unknown command.")

    def move_player(self, direction):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            exits = eval(room[3])
            if direction in exits:
                logging.info(f"User {self.username} moving {direction} from room {self.current_room}.")
                self.untrack_player()
                self.current_room = exits[direction]
                cursor.execute("UPDATE players SET current_room=? WHERE username=?", (self.current_room, self.username))
                conn.commit()
                self.track_player()
                self.display_room()
            else:
                logging.warning(f"Invalid movement {direction} by user {self.username}.")
                self.sendLine(b"You can't go that way.")
        else:
            logging.error(f"Room with ID {self.current_room} not found for movement by user {self.username}.")
            self.sendLine(b"Movement error: Current room not found.")

    def track_player(self):
        if self.current_room not in players_in_rooms:
            players_in_rooms[self.current_room] = []
        players_in_rooms[self.current_room].append(self)
        logging.debug(f"Player {self.username} is now tracked in room {self.current_room}.")

    def untrack_player(self):
        if self.current_room in players_in_rooms:
            players_in_rooms[self.current_room].remove(self)
            logging.debug(f"Player {self.username} is no longer tracked in room {self.current_room}.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
