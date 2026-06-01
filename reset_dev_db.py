import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.json"
BACKUP_DIRECTORY = PROJECT_ROOT / ".local" / "db_backups"


def resolve_database_path(config_path):
    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    database_path = (PROJECT_ROOT / config.get("db_file", "mud_game_10_rooms.db")).resolve()
    if PROJECT_ROOT not in database_path.parents:
        raise ValueError("The development database must stay inside the project directory.")

    return database_path


def archive_database(database_path):
    if not database_path.exists():
        print(f"No development database exists at {database_path.name}.")
        print("Start the server to create a fresh one.")
        return

    BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIRECTORY / f"{database_path.stem}-{timestamp}{database_path.suffix}"
    shutil.move(str(database_path), str(backup_path))

    print(f"Archived {database_path.name} to {backup_path.relative_to(PROJECT_ROOT)}.")
    print("Start the server to create a fresh development database.")


def main():
    parser = argparse.ArgumentParser(
        description="Archive the local SQLite database so the next server launch starts fresh."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the server configuration file.",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    archive_database(resolve_database_path(config_path))


if __name__ == "__main__":
    main()
