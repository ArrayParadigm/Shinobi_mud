import hashlib
import logging
import sqlite3
import unittest

import admin_commands
import shinobi_mud
from command_system import CommandSpec
from migrations import apply_migrations, migration_005_inventory_and_character_foundation


class TestProtocol(shinobi_mud.NinjaMUDProtocol):
    __test__ = False

    def __init__(self, cursor):
        super().__init__(cursor)
        self.messages = []

    def sendLine(self, message):
        self.messages.append(message.decode("utf-8"))

    def display_room(self):
        pass


class AccountLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.players_in_rooms.clear()

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        self.connection.close()

    def create_character(self, username="TestUser", password="secret pass"):
        player = TestProtocol(shinobi_mud.cursor)
        player.handle_username(username)
        player.register_password(password)
        player.confirm_password(password)
        player.choose_specialty("1")
        player.choose_clan("2")
        player.choose_release("1")
        player.allocate_stats("strength=2 dexterity=2 agility=2 intelligence=2 wisdom=2")
        return player

    def test_registration_creates_non_admin_scrypt_account(self):
        player = self.create_character()
        row = self.connection.execute(
            "SELECT * FROM players WHERE username=?",
            (player.username,),
        ).fetchone()

        self.assertEqual(row["is_admin"], 0)
        self.assertTrue(row["password"].startswith("scrypt$"))
        self.assertEqual(row["role_type"], "Ninjutsu")
        self.assertEqual(row["clan"], "Leaf")
        self.assertEqual(row["natural_release"], "Fire")
        self.assertEqual(row["strength"], 7)
        self.assertEqual(player.state, "COMMAND")

    def test_login_restores_saved_character_fields(self):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y, is_admin, role_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("ReturningUser", shinobi_mud.hash_password("password"), 42, 84, 1, "a"),
        )
        self.connection.commit()

        player = TestProtocol(shinobi_mud.cursor)
        player.handle_username("ReturningUser")
        player.handle_password("password")

        self.assertEqual((player.x, player.y), (42, 84))
        self.assertTrue(player.is_admin)
        self.assertEqual(player.player_class, "a")
        self.assertEqual(player.state, "COMMAND")

    def test_legacy_sha256_password_is_upgraded_after_login(self):
        legacy_hash = hashlib.sha256(b"legacy password").hexdigest()
        self.connection.execute(
            "INSERT INTO players (username, password) VALUES (?, ?)",
            ("LegacyUser", legacy_hash),
        )
        self.connection.commit()

        player = TestProtocol(shinobi_mud.cursor)
        player.handle_username("LegacyUser")
        player.handle_password("legacy password")

        stored_hash = self.connection.execute(
            "SELECT password FROM players WHERE username=?",
            ("LegacyUser",),
        ).fetchone()["password"]
        self.assertTrue(stored_hash.startswith("scrypt$"))

    def test_invalid_username_is_rejected(self):
        player = TestProtocol(shinobi_mud.cursor)
        player.handle_username("12")

        self.assertEqual(player.state, "GET_USERNAME")
        self.assertIsNone(player.username)
        self.assertIn("Usernames must be", player.messages[0])

    def test_duplicate_active_session_is_rejected(self):
        first = self.create_character()
        duplicate = TestProtocol(shinobi_mud.cursor)

        duplicate.handle_username(first.username)
        duplicate.handle_password("secret pass")

        self.assertEqual(duplicate.state, "GET_PASSWORD")
        self.assertIn("already logged in", duplicate.messages[-1])

    def test_stat_allocation_rejects_invalid_values(self):
        player = TestProtocol(shinobi_mud.cursor)
        player.handle_username("StatUser")
        player.register_password("password")
        player.confirm_password("password")
        player.choose_specialty("1")
        player.choose_clan("1")
        player.choose_release("5")

        player.allocate_stats("strength=-1 dexterity=2 agility=2 intelligence=2 wisdom=5")
        self.assertEqual(player.state, "ALLOCATE_STATS")

        player.allocate_stats("strength=2 dexterity=2 agility=2 intelligence=2")
        self.assertEqual(player.state, "ALLOCATE_STATS")

        player.allocate_stats("strength=11 dexterity=0 agility=0 intelligence=0 wisdom=0")
        self.assertEqual(player.state, "ALLOCATE_STATS")

    def test_password_input_is_redacted_in_logs(self):
        player = TestProtocol(shinobi_mud.cursor)
        player.state = "REGISTER_PASSWORD"

        with self.assertLogs(level=logging.INFO) as captured:
            player.lineReceived(b"should-not-appear")

        logs = "\n".join(captured.output)
        self.assertIn("Received redacted input", logs)
        self.assertNotIn("should-not-appear", logs)

    def test_character_foundation_migration_preserves_existing_resources(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT NOT NULL,
                health INTEGER,
                stamina INTEGER,
                chakra INTEGER
            )
            """
        )
        connection.execute(
            """
            INSERT INTO players (username, password, health, stamina, chakra)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("LegacyStats", "hash", 17, 13, 21),
        )

        migration_005_inventory_and_character_foundation(connection.cursor())

        player = connection.execute(
            "SELECT * FROM players WHERE username=?",
            ("LegacyStats",),
        ).fetchone()
        self.assertEqual(player["max_health"], 17)
        self.assertEqual(player["max_stamina"], 13)
        self.assertEqual(player["max_chakra"], 21)
        self.assertEqual(player["clan"], "Unaffiliated")
        self.assertEqual(player["natural_release"], "Undeclared")
        connection.close()


class AdminPermissionTests(unittest.TestCase):
    def test_non_admin_is_denied_every_admin_command(self):
        player = TestProtocol(None)
        player.username = "RegularUser"

        for name, command in admin_commands.COMMANDS.items():
            with self.subTest(command=name):
                player.messages.clear()
                command(player, {}, "", [])
                self.assertIn("do not have permission", player.messages[-1])

    def test_admin_metadata_runs_authorized_handler(self):
        player = TestProtocol(None)
        player.username = "AdminUser"
        player.is_admin = True
        calls = []
        command = CommandSpec(
            "admin-test",
            lambda protocol, rooms, raw_args, split_args: calls.append(protocol.username),
            "admin-test",
            "Test command.",
            permission="admin",
        )

        command(player, {}, "", [])

        self.assertEqual(calls, ["AdminUser"])


if __name__ == "__main__":
    unittest.main()
