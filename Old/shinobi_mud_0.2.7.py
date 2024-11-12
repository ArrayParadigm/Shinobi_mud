
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

# Database setup
conn = sqlite3.connect('mud_game_with_full_hardcoded_rooms.db')
cursor = conn.cursor()

# Table for players
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT NOT NULL,
                    current_room INTEGER DEFAULT 1000,
                    village TEXT,
                    rank TEXT DEFAULT 'Genin',
                    chakra INTEGER DEFAULT 100
                )''')

# Hardcoded Celestial Sanctuary Rooms
full_hardcoded_rooms = [
    {"id": 1000, "name": "The Celestial Garden", "description": "A tranquil garden filled with glowing plants under a shimmering starry sky.", "exits": '{"north": 1001, "east": 1002}'},
    {"id": 1001, "name": "The Hall of Echoes", "description": "A grand hall where murals come alive, whispering the stories of past heroes.", "exits": '{"south": 1000, "east": 1010}'},
    {"id": 1002, "name": "The Starlit Path", "description": "A path lined with twinkling stars, stretching into the unknown.", "exits": '{"west": 1000, "north": 1003}'},
    {"id": 1003, "name": "The Reflection Pool", "description": "A calm pool reflecting glimpses of your past and future.", "exits": '{"south": 1002, "east": 1004}'},
    {"id": 1004, "name": "The Archive of Realms", "description": "A vast library of floating books containing the wisdom of countless worlds.", "exits": '{"west": 1003, "north": 1005}'},
    {"id": 1005, "name": "The Chamber of Time", "description": "A chamber where time flows strangely, revealing ancient truths.", "exits": '{"south": 1004, "east": 1006}'},
    {"id": 1006, "name": "The Luminescent Hall", "description": "A radiant hall filled with shimmering lights.", "exits": '{"west": 1005, "north": 1011}'},
    {"id": 1010, "name": "The Hall of Stars", "description": "A chamber with constellations etched into the walls, glowing softly.", "exits": '{"west": 1001, "north": 1020}'},
    {"id": 1011, "name": "The Chamber of Whispers", "description": "A quiet chamber where only the faintest whispers can be heard.", "exits": '{"south": 1006}'},
    {"id": 1020, "name": "The Radiant Chamber", "description": "A glowing room filled with pure energy.", "exits": '{"south": 1010, "east": 1021}'},
    {"id": 1021, "name": "The Corridor of Eternity", "description": "An endless corridor that stretches infinitely.", "exits": '{"west": 1020, "north": 1030}'},
    {"id": 1030, "name": "The Luminous Nexus", "description": "A central nexus where paths converge.", "exits": '{"south": 1021, "east": 1031}'},
    {"id": 1031, "name": "The Crystal Cavern", "description": "A cavern sparkling with thousands of crystals.", "exits": '{"west": 1030, "north": 1032}'},
    {"id": 1032, "name": "The Vault of Secrets", "description": "A place where ancient secrets are kept.", "exits": '{"south": 1031, "east": 1040}'},
    {"id": 1040, "name": "The Mystic Chamber", "description": "A chamber that pulses with mystical energy.", "exits": '{"west": 1032, "north": 1041}'},
    {"id": 1041, "name": "The Reflection Sanctuary", "description": "A serene place for quiet contemplation.", "exits": '{"south": 1040}'},
    # Adding remaining rooms to total at least 30
]

for i in range(1042, 1070):
    full_hardcoded_rooms.append({
        "id": i,
        "name": f"Chamber of Light {i}",
        "description": f"A unique room filled with radiant energy. Room {i}.",
        "exits": "{}"
    })

# Insert all rooms into database
for room in full_hardcoded_rooms:
    cursor.execute("SELECT * FROM rooms WHERE id=?", (room["id"],))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (?, ?, ?, ?)",
                       (room["id"], room["name"], room["description"], room["exits"]))

conn.commit()

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
        self.display_room()

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
        else:
            logging.error(f"Room with ID {self.current_room} not found!")
            self.sendLine(b"Room not found.")

    def handle_command(self, command):
        command = command.decode('utf-8', errors='ignore').strip().lower()
        if command in ["north", "south", "east", "west", "look"]:
            self.sendLine(f"Executed: {command}".encode('utf-8'))
        else:
            logging.warning(f"Unknown command received: {command}")
            self.sendLine(b"Unknown command.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
