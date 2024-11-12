
import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib
import logging

# Logging setup
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("mud_debug.log"),
                        logging.StreamHandler()
                    ])

# Database setup with table creation checks
conn = sqlite3.connect('mud_game_10_rooms.db')
cursor = conn.cursor()

def ensure_tables_exist():
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT NOT NULL,
                        current_room INTEGER DEFAULT 1000,
                        village TEXT,
                        rank TEXT DEFAULT 'Genin',
                        chakra INTEGER DEFAULT 100
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        description TEXT,
                        exits TEXT
                    )''')

ensure_tables_exist()

# Hardcoding 10 rooms in the Celestial Sanctuary
ten_hardcoded_rooms = [
    {"id": 1000, "name": "The Celestial Garden", "description": "A tranquil garden filled with glowing plants under a shimmering starry sky.", "exits": '{"north": 1001, "east": 1002}'},
    {"id": 1001, "name": "The Hall of Echoes", "description": "A grand hall where murals come alive, whispering the stories of past heroes.", "exits": '{"south": 1000, "east": 1003}'},
    {"id": 1002, "name": "The Starlit Path", "description": "A path lined with twinkling stars, stretching into the unknown.", "exits": '{"west": 1000, "north": 1004}'},
    {"id": 1003, "name": "The Chamber of Light", "description": "A room glowing with celestial energy.", "exits": '{"west": 1001}'},
    {"id": 1004, "name": "The Reflection Pool", "description": "A calm pool reflecting your past and future.", "exits": '{"south": 1002, "north": 1005}'},
    {"id": 1005, "name": "The Archive of Realms", "description": "A vast library of floating books containing the wisdom of countless worlds.", "exits": '{"south": 1004, "east": 1006}'},
    {"id": 1006, "name": "The Hall of Stars", "description": "A chamber with constellations etched into the walls.", "exits": '{"west": 1005, "north": 1007}'},
    {"id": 1007, "name": "The Chamber of Whispers", "description": "A quiet room filled with faint whispers.", "exits": '{"south": 1006, "east": 1008}'},
    {"id": 1008, "name": "The Eternal Nexus", "description": "A nexus where all paths converge.", "exits": '{"west": 1007, "north": 1009}'},
    {"id": 1009, "name": "The Throne of Light", "description": "The central point where the Celestial Princess resides.", "exits": '{"south": 1008}'}
]

for room in ten_hardcoded_rooms:
    cursor.execute("SELECT * FROM rooms WHERE id=?", (room["id"],))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (?, ?, ?, ?)",
                       (room["id"], room["name"], room["description"], room["exits"]))

conn.commit()

players_in_rooms = {}

class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None
        self.current_room = 1000

    def connectionMade(self):
        logging.info("New connection established.")
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        logging.debug(f"Received input: {line}")
        if self.state == "GET_USERNAME":
            self.handle_username(line)
        elif self.state == "GET_PASSWORD":
            self.handle_password(line)
        elif self.state == "REGISTER_PASSWORD":
            self.register_password(line)
        else:
            self.handle_command(line)

    def handle_username(self, username):
        username = username.decode('utf-8', errors='ignore').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.current_room = player[3]
            self.sendLine(b"Welcome back, %s! Please enter your password:" % username.encode('utf-8'))
            self.state = "GET_PASSWORD"
        else:
            self.sendLine(b"Username not found. Creating a new account.")
            self.sendLine(b"Choose a password:")
            self.state = "REGISTER_PASSWORD"

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
        else:
            self.sendLine(b"Incorrect password.")

    def register_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO players (username, password, current_room) VALUES (?, ?, ?)", 
                       (self.username, hashed_password, self.current_room))
        conn.commit()

        self.sendLine(b"Account created successfully!")
        self.state = "COMMAND"
        self.track_player()
        self.display_room()

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
            exits = ", ".join(eval(room[3]).keys())
            self.sendLine(f"Exits: {exits}".encode('utf-8'))
            self.list_players_in_room()
        else:
            logging.error(f"Room with ID {self.current_room} not found!")
            self.sendLine(b"Room not found.")

    def list_players_in_room(self):
        others = [p.username for p in players_in_rooms.get(self.current_room, []) if p != self]
        if others:
            self.sendLine(f"Also here: {', '.join(others)}".encode('utf-8'))

    def handle_command(self, command):
        command = command.decode('utf-8', errors='ignore').strip().lower()
        if command in ["north", "south", "east", "west"]:
            self.move_player(command)
        elif command == "look":
            self.display_room()
        else:
            logging.warning(f"Unknown command received: {command}")
            self.sendLine(b"Unknown command.")

    def move_player(self, direction):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            exits = eval(room[3])
            if direction in exits:
                self.untrack_player()
                self.current_room = exits[direction]
                cursor.execute("UPDATE players SET current_room=? WHERE username=?", (self.current_room, self.username))
                conn.commit()
                self.track_player()
                self.display_room()
            else:
                self.sendLine(b"You can't go that way.")
        else:
            logging.error(f"Room with ID {self.current_room} not found for movement.")
            self.sendLine(b"Movement error: Current room not found.")

    def track_player(self):
        if self.current_room not in players_in_rooms:
            players_in_rooms[self.current_room] = []
        players_in_rooms[self.current_room].append(self)

    def untrack_player(self):
        if self.current_room in players_in_rooms:
            players_in_rooms[self.current_room].remove(self)

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
