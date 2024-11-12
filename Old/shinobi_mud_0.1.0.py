
from twisted.internet import protocol, reactor
from twisted.protocols import basic
import sqlite3

# Database setup
conn = sqlite3.connect('mud_game.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    village TEXT,
                    rank TEXT DEFAULT 'Genin',
                    chakra INTEGER DEFAULT 100
                )''')
conn.commit()

class NinjaMUDProtocol(basic.LineReceiver):
    def __init__(self):
        self.state = "GET_USERNAME"
        self.username = None

    def connectionMade(self):
        self.sendLine(b"Welcome to Ninja MUD!")
        self.sendLine(b"Please enter your username:")

    def lineReceived(self, line):
        if self.state == "GET_USERNAME":
            self.handle_username(line)
        elif self.state == "GET_VILLAGE":
            self.handle_village(line)
        else:
            self.handle_command(line)

    def handle_username(self, username):
        username = username.decode('utf-8').strip()
        self.username = username

        cursor.execute("SELECT * FROM players WHERE username=?", (username,))
        player = cursor.fetchone()

        if player:
            self.sendLine(b"Welcome back, %s!" % username.encode('utf-8'))
            self.state = "COMMAND"
        else:
            self.sendLine(b"Username not found. Creating new account.")
            self.sendLine(b"Choose your village: (Leaf, Sand, Mist)")
            self.state = "GET_VILLAGE"

    def handle_village(self, village):
        village = village.decode('utf-8').strip().capitalize()
        if village not in ["Leaf", "Sand", "Mist"]:
            self.sendLine(b"Invalid village. Choose Leaf, Sand, or Mist.")
            return

        cursor.execute("INSERT INTO players (username, village) VALUES (?, ?)",
                       (self.username, village))
        conn.commit()

        self.sendLine(b"Welcome to %s village, %s!" % (village.encode('utf-8'), self.username.encode('utf-8')))
        self.state = "COMMAND"

    def handle_command(self, command):
        command = command.decode('utf-8').strip().lower()

        if command == "look":
            self.sendLine(b"You are in a peaceful village. What would you like to do?")
        elif command == "stats":
            cursor.execute("SELECT * FROM players WHERE username=?", (self.username,))
            player = cursor.fetchone()
            self.sendLine(f"Username: {player[1]}, Village: {player[2]}, Rank: {player[3]}, Chakra: {player[4]}".encode('utf-8'))
        elif command == "help":
            self.sendLine(b"Available commands: look, stats, help.")
        else:
            self.sendLine(b"Unknown command. Type 'help' for options.")

class NinjaMUDFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return NinjaMUDProtocol()

# Start the reactor
reactor.listenTCP(4000, NinjaMUDFactory())
reactor.run()
