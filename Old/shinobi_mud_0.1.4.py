
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import sqlite3
import hashlib

# Database setup
conn = sqlite3.connect('mud_game_enhanced_fixed.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT NOT NULL,
                    village TEXT,
                    rank TEXT DEFAULT 'Genin',
                    chakra INTEGER DEFAULT 100
                )''')
cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    exits TEXT
                )''')
conn.commit()

class NinjaMUDProtocol(basic.LineReceiver):
    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None
        self.password = None
        self.village = None

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
        elif self.state == "GET_VILLAGE":
            self.handle_village(line)
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
            self.sendLine(b"Choose your village: (Leaf, Sand, Mist)")
            self.state = "GET_VILLAGE"

    def handle_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("SELECT * FROM players WHERE username=? AND password=?", (self.username, hashed_password))
        player = cursor.fetchone()

        if player:
            self.sendLine(b"Login successful!")
            self.state = "COMMAND"
            self.send_prompt()
        else:
            self.sendLine(b"Incorrect password. Please try again:")

    def register_password(self, password):
        password = password.decode('utf-8').strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.password = hashed_password

        cursor.execute("INSERT INTO players (username, password, village) VALUES (?, ?, ?)",
                       (self.username, self.password, self.village))
        conn.commit()

        self.sendLine(b"Account created successfully! Welcome, %s!" % self.username.encode('utf-8'))
        self.state = "COMMAND"
        self.send_prompt()

    def handle_village(self, village):
        village = village.decode('utf-8', errors='ignore').strip().capitalize()
        if village not in ["Leaf", "Sand", "Mist"]:
            self.sendLine(b"Invalid village. Choose Leaf, Sand, or Mist.")
            return

        self.village = village
        self.sendLine(b"Set a password for your new account:")
        self.state = "REGISTER_PASSWORD"

    def handle_command(self, command):
        command = command.decode('utf-8', errors='ignore').strip().lower()

        if command == "look":
            self.sendLine(b"You are in a peaceful village. What would you like to do?")
        elif command == "stats":
            cursor.execute("SELECT * FROM players WHERE username=?", (self.username,))
            player = cursor.fetchone()
            self.sendLine(f"Username: {player[1]}, Village: {player[3]}, Rank: {player[4]}, Chakra: {player[5]}".encode('utf-8'))
        elif command == "help":
            self.sendLine(b"Available commands: look, stats, help, say, tell, ooc.")
        elif command.startswith("say "):
            message = command[4:]
            self.sendLine(b'You say: ' + message.encode('utf-8'))
        elif command.startswith("ooc "):
            message = command[4:]
            self.broadcast(f'OOC: {self.username} says: {message}')
        else:
            self.sendLine(b"Unknown command. Type 'help' for options.")

        self.send_prompt()

    def send_prompt(self):
        self.sendLine(b"> ")

    def broadcast(self, message):
        for protocol in self.factory.clients:
            protocol.sendLine(message.encode('utf-8'))

class NinjaMUDFactory(protocol.Factory):
    def __init__(self):
        self.clients = []

    def buildProtocol(self, addr):
        protocol = NinjaMUDProtocol()
        protocol.factory = self
        self.clients.append(protocol)
        return protocol

    def remove_client(self, protocol):
        self.clients.remove(protocol)

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
