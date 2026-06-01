import json
import sqlite3

from content import sync_authored_content
from migrations import apply_migrations, create_players_table
from utils import preload_zones_with_anchors


def main():
    with open("config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    connection = sqlite3.connect(config.get("db_file", "shinobi_mud.db"))
    connection.row_factory = sqlite3.Row
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
    zone_directory = config.get("zone_directory", "zones")
    overlays = preload_zones_with_anchors({}, zone_directory)
    sync_authored_content(connection, zone_directory, overlays)
    connection.close()
    print("Database migrations applied.")


if __name__ == "__main__":
    main()
