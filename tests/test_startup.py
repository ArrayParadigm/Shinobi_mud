import json
import logging
import sqlite3
import tempfile
import unittest
from pathlib import Path

import veilborn_mud


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeReactor:
    def __init__(self):
        self.listened = []
        self.ran = False

    def listenTCP(self, port, factory):
        self.listened.append((port, factory))

    def run(self):
        self.ran = True


class FailingReactor(FakeReactor):
    def run(self):
        raise RuntimeError("reactor smoke failure")


class StartupSmokeTests(unittest.TestCase):
    def setUp(self):
        self.original_config = veilborn_mud.ACTIVE_CONFIG.copy()
        self.original_overlays = veilborn_mud.WORLD_OVERLAYS.copy()

    def tearDown(self):
        if veilborn_mud.conn:
            veilborn_mud.conn.close()
            veilborn_mud.conn = None
            veilborn_mud.cursor = None
        veilborn_mud.ACTIVE_CONFIG.clear()
        veilborn_mud.ACTIVE_CONFIG.update(self.original_config)
        veilborn_mud.WORLD_OVERLAYS.clear()
        veilborn_mud.WORLD_OVERLAYS.update(self.original_overlays)

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

            config = veilborn_mud.run_server(str(config_path), fake_reactor)

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
            self.assertTrue(
                {
                    "players",
                    "rooms",
                    "schema_migrations",
                    "item_definitions",
                    "room_items",
                    "character_inventory",
                    "authored_content_seeds",
                    "npc_templates",
                    "npc_instances",
                    "skill_definitions",
                    "expression_definitions",
                    "character_skills",
                    "character_expressions",
                    "character_expression_states",
                    "stance_definitions",
                    "character_stances",
                    "combat_engagements",
                    "combat_action_queue",
                    "combat_technique_definitions",
                }
                <= tables
            )
            self.assertGreaterEqual(len(veilborn_mud.WORLD_OVERLAYS), 30)
            self.assertEqual(veilborn_mud.WORLD_OVERLAYS[(500, 500)]["vnum"], 3000)
            self.assertEqual(veilborn_mud.WORLD_OVERLAYS[(1, 1)]["vnum"], 1000)
            veilborn_mud.conn.close()
            veilborn_mud.conn = None
            veilborn_mud.cursor = None

    def test_validation_rejects_invalid_port(self):
        veilborn_mud.conn = sqlite3.connect(":memory:")
        veilborn_mud.conn.row_factory = sqlite3.Row
        veilborn_mud.cursor = veilborn_mud.conn.cursor()
        veilborn_mud.ensure_tables_exist(veilborn_mud.conn)
        veilborn_mud.apply_migrations(veilborn_mud.conn)
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.load_commands()
        with self.assertRaises(RuntimeError):
            veilborn_mud.validate_server_state(
                {
                    "server_port": "not-a-port",
                    "zone_directory": str(PROJECT_ROOT / "zones"),
                }
            )

    def test_validation_rejects_non_boolean_color_default(self):
        veilborn_mud.conn = sqlite3.connect(":memory:")
        veilborn_mud.conn.row_factory = sqlite3.Row
        veilborn_mud.cursor = veilborn_mud.conn.cursor()
        veilborn_mud.ensure_tables_exist(veilborn_mud.conn)
        veilborn_mud.apply_migrations(veilborn_mud.conn)
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.load_commands()
        with self.assertRaises(RuntimeError):
            veilborn_mud.validate_server_state(
                {
                    "default_color_enabled": "yes",
                    "zone_directory": str(PROJECT_ROOT / "zones"),
                }
            )

    def test_configure_logging_creates_nested_log_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "logs" / "smoke.log"

            veilborn_mud.configure_logging(str(log_path))
            logging.info("logging smoke test")

            self.assertTrue(log_path.exists())
            veilborn_mud.configure_logging()

        self.assertEqual(Path(veilborn_mud.DEFAULT_LOG_FILE).parts[0], "logs")

    def test_run_server_logs_unexpected_reactor_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp = Path(temporary_directory)
            config_path = temp / "config.json"
            log_path = temp / "logs" / "failure.log"
            config_path.write_text(
                json.dumps(
                    {
                        "db_file": str(temp / "smoke.db"),
                        "log_file": str(log_path),
                        "motd_file": str(PROJECT_ROOT / "motd.txt"),
                        "server_port": 4567,
                        "zone_directory": str(PROJECT_ROOT / "zones"),
                    }
                ),
                encoding="utf-8",
            )

            try:
                with self.assertRaisesRegex(RuntimeError, "reactor smoke failure"):
                    veilborn_mud.run_server(str(config_path), FailingReactor())
            finally:
                veilborn_mud.conn.close()
                veilborn_mud.configure_logging()

            self.assertIn("Unexpected server failure.", log_path.read_text())


if __name__ == "__main__":
    unittest.main()
