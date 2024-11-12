
import os
import json
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib

# Database setup
conn = sqlite3.connect('mud_game_with_commands.db')
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

# Player tracking
players_in_rooms = {}

class CommandHandler:
    def __init__(self, protocol):
        self.protocol = protocol
        self.commands = {
            "look": self.cmd_look,
            "north": self.cmd_move,
            "south": self.cmd_move,
            "east": self.cmd_move,
            "west": self.cmd_move,
            "say": self.cmd_say,
            "ooc": self.cmd_ooc,
            "stats": self.cmd_stats
        }

    def handle(self, command):
        parts = command.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd in self.commands:
            self.commands[cmd](arg)
        else:
            self.protocol.sendLine(b"Unknown command. Try 'look', 'say', 'stats', etc.")

    # Command Implementations
    def cmd_look(self, _):
        self.protocol.display_room()

    def cmd_move(self, direction):
        self.protocol.move_player(direction)

    def cmd_say(self, message):
        if not message:
            self.protocol.sendLine(b"Say what?")
            return
        self.protocol.broadcast_to_room(f"{self.protocol.username} says: {message}")

    def cmd_ooc(self, message):
        if not message:
            self.protocol.sendLine(b"OOC what?")
            return
        self.protocol.broadcast_global(f"OOC {self.protocol.username}: {message}")

    def cmd_stats(self, _):
        self.protocol.sendLine(f"Username: {self.protocol.username}, Room: {self.protocol.current_room}".encode('utf-8'))


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

        # Insert new player starting in the Celestial Garden
        cursor.execute("INSERT INTO players (username, password, current_room) VALUES (?, ?, ?)", 
                       (self.username, hashed_password, self.current_room))
        conn.commit()

        self.sendLine(b"Account created successfully!")
        self.state = "COMMAND"
        self.track_player()
        self.display_room()

    def track_player(self):
        if self.current_room not in players_in_rooms:
            players_in_rooms[self.current_room] = []
        players_in_rooms[self.current_room].append(self)

    def untrack_player(self):
        if self.current_room in players_in_rooms:
            players_in_rooms[self.current_room].remove(self)

    def display_room(self):
        cursor.execute("SELECT * FROM rooms WHERE id=?", (self.current_room,))
        room = cursor.fetchone()

        if room:
            self.sendLine(f"You are in {room[1]}. {room[2]}".encode('utf-8'))
            exits = ", ".join(eval(room[3]).keys())
            self.sendLine(f"Exits: {exits}".encode('utf-8'))
            self.notify_room_presence()
        else:
            self.sendLine(b"Error: Room not found.")

    def notify_room_presence(self):
        other_players = [p.username for p in players_in_rooms[self.current_room] if p != self]
        if other_players:
            self.sendLine(f"Also here: {', '.join(other_players)}".encode('utf-8'))

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
            self.sendLine(b"Error: Room not found.")

    def broadcast_to_room(self, message):
        for player in players_in_rooms.get(self.current_room, []):
            player.sendLine(message.encode('utf-8'))

    def broadcast_global(self, message):
        for room_players in players_in_rooms.values():
            for player in room_players:
                player.sendLine(message.encode('utf-8'))


class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        protocol = NinjaMUDProtocol()
        protocol.command_handler = CommandHandler(protocol)
        return protocol

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
