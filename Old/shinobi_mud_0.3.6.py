
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
                        is_admin BOOLEAN DEFAULT 0,
                        role_type INTEGER DEFAULT 4, -- default to Newbie
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
        logging.debug(f"Received input: {line}")
        try:
            if self.state == "GET_USERNAME":
                self.handle_username(line)
            elif self.state == "GET_PASSWORD":
                self.handle_password(line)
            elif self.state == "REGISTER_PASSWORD":
                self.register_password(line)
            elif self.state == "CONFIRM_PASSWORD":
                self.confirm_password(line)
            elif self.state == "SELECT_ROLE":
                self.select_role(line)
            elif self.state == "ALLOCATE_STATS":
                self.allocate_stats(line)
            elif self.state == "CHOOSE_DOJO":
                self.choose_dojo(line)
            else:
                self.handle_command(line)
        except Exception as e:
            logging.error(f"Error processing input {line}: {e}", exc_info=True)
            self.sendLine(b"An error occurred. Please try again.")

    # The rest of the methods remain unchanged from the previously reviewed file

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
