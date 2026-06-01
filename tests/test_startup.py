import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import shinobi_mud


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeReactor:
    def __init__(self):
        self.listened = []
        self.ran = False

    def listenTCP(self, port, factory):
        self.listened.append((port, factory))

    def run(self):
        self.ran = True


class StartupSmokeTests(unittest.TestCase):
    def tearDown(self):
        if shinobi_mud.conn:
            shinobi_mud.conn.close()

    def test_run_server_initializes_and_uses_configured_port(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp = Path(temporary_directory)
            config_path = temp / "config.json"
            database_path = temp / "smoke.db"
            config_path.write_text(
                json.dumps(
                    {
                        "db_file": str(database_path),
                        "motd_file": str(PROJECT_ROOT / "motd.txt"),
                        "server_port": 4567,
                        "zone_directory": str(PROJECT_ROOT / "zones"),
                    }
                ),
                encoding="utf-8",
            )
            fake_reactor = FakeReactor()

            config = shinobi_mud.run_server(str(config_path), fake_reactor)

            self.assertEqual(config["server_port"], 4567)
            self.assertEqual(fake_reactor.listened[0][0], 4567)
            self.assertTrue(fake_reactor.ran)
            connection = sqlite3.connect(database_path)
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            connection.close()
            self.assertTrue({"players", "rooms", "schema_migrations"} <= tables)
            shinobi_mud.conn.close()

    def test_validation_rejects_invalid_port(self):
        shinobi_mud.conn = sqlite3.connect(":memory:")
        shinobi_mud.conn.row_factory = sqlite3.Row
        shinobi_mud.cursor = shinobi_mud.conn.cursor()
        shinobi_mud.ensure_tables_exist(shinobi_mud.conn)
        shinobi_mud.apply_migrations(shinobi_mud.conn)
        shinobi_mud.COMMAND_REGISTRY.clear()
        shinobi_mud.load_commands()
        with self.assertRaises(RuntimeError):
            shinobi_mud.validate_server_state(
                {
                    "server_port": "not-a-port",
                    "zone_directory": str(PROJECT_ROOT / "zones"),
                }
            )


if __name__ == "__main__":
    unittest.main()
