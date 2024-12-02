import sqlite3

# Connect to your database
conn = sqlite3.connect('mud_game_10_rooms.db')
cursor = conn.cursor()

# Add new columns if they do not already exist
try:
    cursor.execute("ALTER TABLE players ADD COLUMN x INTEGER DEFAULT 0;")
    print("Added column 'x'")
except sqlite3.OperationalError as e:
    print(f"Column 'x' might already exist: {e}")

try:
    cursor.execute("ALTER TABLE players ADD COLUMN y INTEGER DEFAULT 0;")
    print("Added column 'y'")
except sqlite3.OperationalError as e:
    print(f"Column 'y' might already exist: {e}")

try:
    cursor.execute("ALTER TABLE players ADD COLUMN in_zone BOOLEAN DEFAULT 0;")
    print("Added column 'in_zone'")
except sqlite3.OperationalError as e:
    print(f"Column 'in_zone' might already exist: {e}")

# Commit changes and close the connection
conn.commit()
conn.close()
