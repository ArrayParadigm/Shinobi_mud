
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import sqlite3
import hashlib

# Database setup
conn = sqlite3.connect('mud_game_with_rooms.db')
cursor = conn.cursor()

# Table for players
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT NOT NULL,
                    current_room INTEGER DEFAULT 1,
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

# Add a default starting room if it doesn't exist
cursor.execute("SELECT * FROM rooms WHERE id=1")
if not cursor.fetchone():
    cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (1, 'Village Square', 'You are in a bustling village square. Exits lead north and east.', '{"north": 2, "east": 3}')")
    cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (2, 'Training Ground', 'This is a wide open field for training.', '{"south": 1}')")
    cursor.execute("INSERT INTO rooms (id, name, description, exits) VALUES (3, 'Marketplace', 'A lively marketplace full of vendors.', '{"west": 1}')")
conn.commit()

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
        self.current_room = 1
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
            self.sendLine(b"Error: Room not found.")

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
