import sqlite3
import os
import hashlib
import json
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Factory
from twisted.internet import reactor
import logging

logging.basicConfig(filename="mud_debug.log", level=logging.DEBUG)

DB_PATH = "mud_game_10_rooms.db"

class NinjaMUDProtocol(LineReceiver):
    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None
        self.password = None
        self.remaining_points = 0
        self.stats = {}
        self.dojo = None

    def lineReceived(self, line):
        line = line.strip()
        if self.state == "GET_USERNAME":
            self.handle_username(line.decode("utf-8"))
        elif self.state == "GET_PASSWORD":
            self.handle_password(line.decode("utf-8"))
        elif self.state == "ALLOCATE_STATS":
            self.allocate_stat(line.decode("utf-8"))
        elif self.state == "SELECT_DOJO":
            self.assign_dojo(line.decode("utf-8"))
        else:
            self.execute_command(line.decode("utf-8"))

    def handle_username(self, username):
        self.username = username
        self.sendLine(b"Welcome, " + self.username.encode('utf-8') + b"! Please enter your password:")
        self.state = "GET_PASSWORD"

    def handle_password(self, password):
        self.password = password
        if self.is_new_player():
            self.sendLine(b"Character not found. Starting character creation.")
            self.start_character_creation()
        else:
            if self.validate_login():
                self.sendLine(b"Login successful!")
                self.state = "PLAYING"
            else:
                self.sendLine(b"Invalid password.")

    def is_new_player(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM players WHERE username = ?", (self.username,))
        is_new = cursor.fetchone() is None
        conn.close()
        return is_new

    def validate_login(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM players WHERE username = ?", (self.username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            hashed_pw = hashlib.sha256(self.password.encode('utf-8')).hexdigest()
            return result[0] == hashed_pw
        return False

    def start_character_creation(self):
        self.sendLine(b"Distribute 30 points among the following stats:")
        self.sendLine(b"Health, Stamina, Chakra, Strength, Dexterity, Agility, Intelligence, Wisdom.")
        self.remaining_points = 30
        self.stats = {"health": 0, "stamina": 0, "chakra": 0, "strength": 0, "dexterity": 0, "agility": 0, "intelligence": 0, "wisdom": 0}
        self.prompt_stat_allocation()

    def prompt_stat_allocation(self):
        self.sendLine(b"Remaining points: " + str(self.remaining_points).encode('utf-8'))
        self.sendLine(b"Allocate points. Example: 'health 5'")

    def allocate_stat(self, stat_line):
        try:
            stat, points = stat_line.split()
            points = int(points)
            if stat in self.stats and self.remaining_points >= points:
                self.stats[stat] += points
                self.remaining_points -= points
                if self.remaining_points > 0:
                    self.prompt_stat_allocation()
                else:
                    self.sendLine(b"Stat allocation complete!")
                    self.select_dojo()
            else:
                raise ValueError
        except ValueError:
            self.sendLine(b"Invalid input or not enough points.")
            self.prompt_stat_allocation()

    def select_dojo(self):
        self.sendLine(b"Choose your dojo:")
        self.sendLine(b"1. Taijutsu Dojo (Physical Strength)")
        self.sendLine(b"2. Genjutsu Dojo (Illusion Mastery)")
        self.sendLine(b"3. Ninjutsu Dojo (Elemental Techniques)")
        self.state = "SELECT_DOJO"

    def assign_dojo(self, dojo_choice):
        dojo_map = {"1": "Taijutsu Dojo", "2": "Genjutsu Dojo", "3": "Ninjutsu Dojo"}
        self.dojo = dojo_map.get(dojo_choice.strip(), "Unaligned")
        self.sendLine(b"Character creation complete! You are now aligned with " + self.dojo.encode('utf-8') + b".")
        self.save_player_data()

    def save_player_data(self):
        hashed_pw = hashlib.sha256(self.password.encode('utf-8')).hexdigest()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players (username, password, health, stamina, chakra, strength, dexterity, agility, intelligence, wisdom, current_room, dojo, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.username, hashed_pw, self.stats["health"], self.stats["stamina"], self.stats["chakra"], self.stats["strength"], 
              self.stats["dexterity"], self.stats["agility"], self.stats["intelligence"], self.stats["wisdom"], 1000, self.dojo, 4))
        conn.commit()
        conn.close()
        self.sendLine(b"Your character has been saved! Welcome to the game.")

    def execute_command(self, command_line):
        self.sendLine(b"Command system not yet implemented in this merge.")

class NinjaMUDFactory(Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
