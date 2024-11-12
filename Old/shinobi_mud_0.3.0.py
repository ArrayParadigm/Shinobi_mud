
import os
import sqlite3
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import hashlib
import logging

# Importing commands from different categories
from general_commands import COMMANDS as general_commands
from admin_commands import COMMANDS as admin_commands

# Merging command registries
COMMAND_REGISTRY = {**general_commands, **admin_commands}

# Logging setup
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("mud_debug.log"),
                        logging.StreamHandler()
                    ])

# Database setup
conn = sqlite3.connect('mud_game_modular_commands.db')
cursor = conn.cursor()

def ensure_tables_exist():
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT NOT NULL,
                        current_room INTEGER DEFAULT 1000,
                        is_admin BOOLEAN DEFAULT 0
                    )''')

ensure_tables_exist()

class NinjaMUDProtocol(basic.LineReceiver):
    delimiter = b"\n"

    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None
        self.is_admin = False

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
        username = username.decode('utf-8').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.is_admin = bool(player[4])
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
        else:
            self.sendLine(b"Incorrect password.")

    def register_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO players (username, password, current_room) VALUES (?, ?, ?)", 
                       (self.username, hashed_password, 1000))
        conn.commit()
        self.sendLine(b"Account created successfully!")
        self.state = "COMMAND"

    def handle_command(self, command):
        command = command.decode('utf-8').strip().lower()
        handler = COMMAND_REGISTRY.get(command)
        if handler:
            handler(self)
        else:
            self.sendLine(b"Unknown command.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
