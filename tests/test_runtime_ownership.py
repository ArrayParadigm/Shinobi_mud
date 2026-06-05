import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import general_commands
import veilborn_mud
from content import sync_authored_content
from migrations import apply_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeOwnershipTests(unittest.TestCase):
    def setUp(self):
        veilborn_mud.players_in_rooms.clear()

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        if veilborn_mud.conn:
            veilborn_mud.conn.close()
            veilborn_mud.conn = None
            veilborn_mud.cursor = None

    def initialize_database(self, database_path):
        connection = veilborn_mud.connect_database(str(database_path))
        veilborn_mud.ensure_tables_exist(connection)
        apply_migrations(connection)
        veilborn_mud.UTILITIES["preload_zones_with_anchors"](
            veilborn_mud.WORLD_OVERLAYS,
            str(PROJECT_ROOT / "zones"),
        )
        sync_authored_content(connection, str(PROJECT_ROOT / "zones"), veilborn_mud.WORLD_OVERLAYS)
        return connection

    def write_config(self, config_path, database_path):
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

    def test_factory_builds_protocols_with_distinct_owned_connections(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            maintenance_connection = self.initialize_database(database_path)
            factory = veilborn_mud.VeilbornMUDFactory(str(database_path))

            first = factory.buildProtocol(None)
            second = factory.buildProtocol(None)

            self.assertTrue(first.owns_connection)
            self.assertTrue(second.owns_connection)
            self.assertIsNot(first.connection, second.connection)
            self.assertIsNot(first.connection, maintenance_connection)
            self.assertEqual(first.cursor.execute("SELECT 1").fetchone()[0], 1)
            self.assertEqual(second.cursor.execute("SELECT 1").fetchone()[0], 1)
            first.connectionLost("test disconnect")
            with self.assertRaises(sqlite3.ProgrammingError):
                first.cursor.execute("SELECT 1")
            self.assertEqual(second.cursor.execute("SELECT 1").fetchone()[0], 1)
            second.connectionLost("test disconnect")
            maintenance_connection.close()

    def test_prelogin_disconnect_closes_connection_without_broadcast(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            maintenance_connection = self.initialize_database(database_path)
            observer = type("Observer", (), {"messages": [], "sendLine": lambda self, message: self.messages.append(message.decode("utf-8"))})()
            veilborn_mud.players_in_rooms[(500, 500)] = [observer]
            player = veilborn_mud.VeilbornMUDFactory(str(database_path)).buildProtocol(None)
            player.username = "NotLoggedIn"

            player.connectionLost("test disconnect")

            self.assertEqual(observer.messages, [])
            self.assertTrue(player.connection_closed)
            maintenance_connection.close()

    def test_factory_session_runs_player_command_on_its_owned_connection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            maintenance_connection = self.initialize_database(database_path)
            player = veilborn_mud.VeilbornMUDFactory(str(database_path)).buildProtocol(None)
            player.messages = []
            player.sendLine = lambda message: player.messages.append(message.decode("utf-8"))
            player.username = "SessionUser"
            player.cursor.execute(
                "INSERT INTO players (username, password) VALUES (?, ?)",
                (player.username, "hash"),
            )
            player.connection.commit()

            general_commands.handle_score(player)

            self.assertEqual(player.messages[0], "Score for SessionUser")
            player.connectionLost("test disconnect")
            maintenance_connection.close()

    def test_repeated_initialization_replaces_only_maintenance_connection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp = Path(temporary_directory)
            first_config = temp / "first.json"
            second_config = temp / "second.json"
            self.write_config(first_config, temp / "first.db")
            self.write_config(second_config, temp / "second.db")

            veilborn_mud.initialize_server(str(first_config))
            first_connection = veilborn_mud.conn
            session = veilborn_mud.VeilbornMUDFactory(str(temp / "first.db")).buildProtocol(None)
            veilborn_mud.initialize_server(str(second_config))

            with self.assertRaises(sqlite3.ProgrammingError):
                first_connection.execute("SELECT 1")
            self.assertEqual(session.cursor.execute("SELECT 1").fetchone()[0], 1)
            self.assertEqual(veilborn_mud.conn.execute("SELECT 1").fetchone()[0], 1)
            session.connectionLost("test disconnect")
            veilborn_mud.conn.close()
            veilborn_mud.conn = None
            veilborn_mud.cursor = None

    def test_world_tick_uses_maintenance_connection_after_session_disconnect(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            veilborn_mud.conn = self.initialize_database(database_path)
            veilborn_mud.cursor = veilborn_mud.conn.cursor()
            session = veilborn_mud.VeilbornMUDFactory(str(database_path)).buildProtocol(None)
            session.connectionLost("test disconnect")

            expected_updates = veilborn_mud.conn.execute(
                "SELECT COUNT(*) FROM npc_instances"
            ).fetchone()[0]
            updated = veilborn_mud.run_world_tick()
            veilborn_mud.conn.close()
            veilborn_mud.conn = None
            veilborn_mud.cursor = None
            self.assertEqual(updated, expected_updates)


if __name__ == "__main__":
    unittest.main()
