import argparse
import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Promote an existing local MUD account to admin.")
    parser.add_argument("username", help="Existing account to promote.")
    parser.add_argument("--config", default="config.json", help="Server configuration file.")
    args = parser.parse_args()

    config_path = (PROJECT_ROOT / args.config).resolve()
    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    database_path = (PROJECT_ROOT / config.get("db_file", "mud_game_10_rooms.db")).resolve()
    connection = sqlite3.connect(database_path)
    cursor = connection.execute(
        "UPDATE players SET is_admin=1 WHERE username=?",
        (args.username,),
    )
    connection.commit()
    connection.close()

    if cursor.rowcount != 1:
        raise SystemExit(f"No account named {args.username!r} exists.")
    print(f"Promoted {args.username!r} to admin.")


if __name__ == "__main__":
    main()
