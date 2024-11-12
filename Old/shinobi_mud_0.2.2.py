
import os
import json
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib

# Database setup
conn = sqlite3.connect('mud_game_with_expanded_eve_domain.db')
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

# Eve's expanded domain with proper JSON formatting for exits
expanded_eve_domain_rooms = [
    {"id": 1000, "name": "The Celestial Garden", "description": "A tranquil garden filled with glowing plants under a shimmering starry sky.", "exits": '{"north": 1001, "east": 1002}'},
    {"id": 1001, "name": "The Hall of Echoes", "description": "A grand hall where murals come alive, whispering the stories of past heroes.", "exits": '{"south": 1000}'},
    {"id": 1002, "name": "The Starlit Path", "description": "A path lined with twinkling stars, stretching into the unknown.", "exits": '{"west": 1000, "north": 1003}'},
    {"id": 1003, "name": "The Reflection Pool", "description": "A calm pool that reflects not only your image but also glimpses of your past and future.", "exits": '{"south": 1002, "east": 1004}'},
    {"id": 1004, "name": "The Archive of Realms", "description": "A vast library of floating books containing the wisdom of countless worlds.", "exits": '{"west": 1003}'}
]

# Add more secret rooms to the domain dynamically (keeping it hidden for excitement!)
for room_id in range(1005, 1020):  # Adding more hidden rooms dynamically
    expanded_eve_domain_rooms.append({
        "id": room_id,
        "name": f"Mystic Chamber {room_id}",
        "description": f"A mysterious chamber filled with ethereal energy. Room {room_id} holds a secret of its own.",
        "exits": "{}"  # Default placeholder for hidden connectivity
    })

# Insert rooms into the database
for room in expanded_eve_domain_rooms:
    cursor.execute("SELECT * FROM rooms WHERE id=?", (room["id"],))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (?, ?, ?, ?)",
                       (room["id"], room["name"], room["description"], room["exits"]))

conn.commit()

# Function to load external zones
def load_zones(directory="zones"):
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            with open(os.path.join(directory, filename), 'r') as f:
                zone_data = json.load(f)
                for room in zone_data["rooms"]:
                    cursor.execute("SELECT * FROM rooms WHERE id=?", (room["id"],))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (?, ?, ?, ?)",
                                       (room["id"], room["name"], room["description"], json.dumps(room["exits"])))
    conn.commit()

# Load all zones at startup
load_zones()

class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None

    def connectionMade(self):
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        if self.state == "GET_USERNAME":
            self.handle_username(line)
        elif self.state == "GET_PASSWORD":
            self.handle_password(line)
        else:
            self.handle_command(line)

    def handle_username(self, username):
        username = username.decode('utf-8', errors='ignore').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
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
            self.current_room = player[3]
            self.display_room()
        else:
            self.sendLine(b"Incorrect password. Please try again:")

    def register_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("INSERT INTO players (username, password) VALUES (?, ?)", (self.username, hashed_password))
        conn.commit()

        self.sendLine(b"Account created successfully!")
        self.state = "COMMAND"
        self.current_room = 1000  # Start in the Celestial Garden
        self.display_room()

    def handle_command(self, command):
        command = command.decode('utf-8', errors='ignore').strip().lower()

        if command in ["north", "south", "east", "west"]:
            self.move_player(command)
        elif command == "look":
            self.display_room()
        else:
            self.sendLine(b"Unknown command. Available commands: north, south, east, west, look.")

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
            exits = ", ".join(eval(room[3]).keys())
            self.sendLine(f"Exits: {exits}".encode('utf-8'))
        else:
            self.sendLine(b"Error: Room not found. Moving you to the Celestial Garden.")
            self.current_room = 1000
            self.display_room()

    def move_player(self, direction):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            exits = eval(room[3])
            if direction in exits:
                self.current_room = exits[direction]
                cursor.execute("UPDATE players SET current_room=? WHERE username=?", (self.current_room, self.username))
                conn.commit()
                self.display_room()
            else:
                self.sendLine(b"You can't go that way.")
        else:
            self.sendLine(b"Error: Room not found.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
