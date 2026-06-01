import json
import sqlite3

from migrations import apply_migrations, create_players_table


def main():
    with open("config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    connection = sqlite3.connect(config.get("db_file", "mud_game_10_rooms.db"))
    cursor = connection.cursor()
    create_players_table(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            exits TEXT
        )
        """
    )
    connection.commit()
    apply_migrations(connection)
    connection.close()
    print("Database migrations applied.")


if __name__ == "__main__":
    main()
