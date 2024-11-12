
import os
import json
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib

# Database setup
conn = sqlite3.connect('mud_game_with_expanded_sanctuary.db')
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

# Table for rooms
cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    exits TEXT
                )''')

# Hardcoded Celestial Sanctuary Rooms (Expanding to 30+ Rooms)
expanded_sanctuary_rooms = [
    {"id": 1000, "name": "The Celestial Garden", "description": "A tranquil garden filled with glowing plants under a shimmering starry sky.", "exits": '{"north": 1001, "east": 1002}'},
    {"id": 1001, "name": "The Hall of Echoes", "description": "A grand hall where murals come alive, whispering the stories of past heroes.", "exits": '{"south": 1000, "east": 1010}'},
    {"id": 1002, "name": "The Starlit Path", "description": "A path lined with twinkling stars, stretching into the unknown.", "exits": '{"west": 1000, "north": 1003}'},
    {"id": 1003, "name": "The Reflection Pool", "description": "A calm pool reflecting glimpses of your past and future.", "exits": '{"south": 1002, "east": 1004}'},
    {"id": 1004, "name": "The Archive of Realms", "description": "A vast library of floating books containing the wisdom of countless worlds.", "exits": '{"west": 1003, "north": 1005}'},
    {"id": 1005, "name": "The Chamber of Time", "description": "A chamber where time flows strangely, revealing ancient truths.", "exits": '{"south": 1004, "west": 1011}'},
    {"id": 1010, "name": "The Hall of Stars", "description": "A chamber with constellations etched into the walls, glowing softly.", "exits": '{"west": 1001, "north": 1020}'},
    {"id": 1011, "name": "The Veil of Whispers", "description": "An eerie room filled with the faint echoes of forgotten voices.", "exits": '{"east": 1005}'},
    {"id": 1020, "name": "The Radiant Chamber", "description": "A glowing room filled with pure energy, illuminating your path.", "exits": '{"south": 1010, "east": 1021}'},
    {"id": 1021, "name": "The Corridor of Eternity", "description": "An endless corridor that seems to stretch forever.", "exits": '{"west": 1020, "north": 1030}'},
    {"id": 1030, "name": "The Luminous Hall", "description": "An ethereal hall where light dances freely.", "exits": '{"south": 1021, "east": 1031}'},
    {"id": 1031, "name": "The Prism Chamber", "description": "A room filled with refracted light, creating a kaleidoscope of colors.", "exits": '{"west": 1030}'},
    # Adding additional unique rooms to expand the sanctuary
]

# Fill sanctuary with at least 30 unique rooms dynamically
for room_id in range(1032, 1060):
    expanded_sanctuary_rooms.append({
        "id": room_id,
        "name": f"Ethereal Chamber {room_id}",
        "description": f"A unique chamber emanating otherworldly energy. Secrets abound here. Room {room_id}.",
        "exits": "{}"  # Will later dynamically connect rooms as needed
    })

# Insert sanctuary rooms into the database
for room in expanded_sanctuary_rooms:
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
        self.current_room = 1000  # Default starting room

    def connectionMade(self):
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        if self.state == "GET_USERNAME":
            self.handle_username(line)
        elif self.state == "GET_PASSWORD":
            self.handle_password(line)
        elif self.state == "REGISTER_PASSWORD":
            self.register_password(line)
        else:
            self.handle_command(line)

    def handle_command(self, line):
        command = line.decode('utf-8', errors='ignore').strip().lower()
        if hasattr(self, 'command_handler'):
            self.command_handler.handle(command)

    def handle_username(self, username):
        username = username.decode('utf-8', errors='ignore').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.current_room = player[3]  # Load player's last room
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
            self.sendLine(b"Incorrect password. Please try again:")

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

    def track_player(self):
        pass  # Player tracking logic placeholder

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
        else:
            self.sendLine(b"Error: Room not found.")

    def handle_command(self, command):
        pass  # Placeholder for command handling logic


class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
