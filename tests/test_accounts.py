import hashlib
import logging
import sqlite3
import unittest

import admin_commands
import veilborn_mud
from command_system import CommandSpec
from migrations import apply_migrations, migration_005_inventory_and_character_foundation


class TestProtocol(veilborn_mud.VeilbornMUDProtocol):
    __test__ = False

    def __init__(self, cursor):
        super().__init__(cursor)
        self.messages = []
        self.color_enabled = False

    def sendLine(self, message):
        self.messages.append(message.decode("utf-8"))

    def display_room(self):
        pass


class AccountLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.players_in_rooms.clear()

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        self.connection.close()

    def create_character(self, username="TestUser", password="secret pass"):
        player = TestProtocol(veilborn_mud.cursor)
        player.handle_username(username)
        player.register_password(password)
        player.confirm_password(password)
        return player

    def test_registration_creates_non_admin_scrypt_account(self):
        player = self.create_character()
        row = self.connection.execute(
            "SELECT * FROM players WHERE username=?",
            (player.username,),
        ).fetchone()

        self.assertEqual(row["is_admin"], 0)
        self.assertEqual(row["is_builder"], 0)
        self.assertTrue(row["password"].startswith("scrypt$"))
        self.assertEqual(row["role_type"], "newbie")
        self.assertEqual(row["clan"], "Unaffiliated")
        self.assertEqual(row["essence"], "Undeclared")
        self.assertEqual(row["strength"], 10)
        self.assertEqual(row["dexterity"], 10)
        self.assertEqual(row["agility"], 10)
        self.assertEqual(row["intelligence"], 10)
        self.assertEqual(row["wisdom"], 10)
        self.assertIsNotNone(row["created_at"])
        self.assertIsNotNone(row["last_login_at"])
        self.assertEqual(player.state, "COMMAND")

    def test_login_restores_saved_character_fields(self):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y, is_admin, role_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("ReturningUser", veilborn_mud.hash_password("password"), 42, 84, 1, "a"),
        )
        self.connection.commit()

        player = TestProtocol(veilborn_mud.cursor)
        player.handle_username("ReturningUser")
        player.handle_password("password")

        self.assertEqual((player.x, player.y), (42, 84))
        self.assertTrue(player.is_admin)
        self.assertFalse(player.is_builder)
        self.assertEqual(player.player_class, "a")
        self.assertEqual(player.state, "COMMAND")
        last_login = self.connection.execute(
            "SELECT last_login_at FROM players WHERE username='ReturningUser'"
        ).fetchone()["last_login_at"]
        self.assertIsNotNone(last_login)

    def test_legacy_sha256_password_is_upgraded_after_login(self):
        legacy_hash = hashlib.sha256(b"legacy password").hexdigest()
        self.connection.execute(
            "INSERT INTO players (username, password) VALUES (?, ?)",
            ("LegacyUser", legacy_hash),
        )
        self.connection.commit()

        player = TestProtocol(veilborn_mud.cursor)
        player.handle_username("LegacyUser")
        player.handle_password("legacy password")

        stored_hash = self.connection.execute(
            "SELECT password FROM players WHERE username=?",
            ("LegacyUser",),
        ).fetchone()["password"]
        self.assertTrue(stored_hash.startswith("scrypt$"))

    def test_invalid_username_is_rejected(self):
        player = TestProtocol(veilborn_mud.cursor)
        player.handle_username("12")

        self.assertEqual(player.state, "GET_USERNAME")
        self.assertIsNone(player.username)
        self.assertIn("Usernames must be", player.messages[0])

    def test_duplicate_active_session_takes_over_existing_body(self):
        first = self.create_character()
        duplicate = TestProtocol(veilborn_mud.cursor)

        duplicate.handle_username(first.username)
        duplicate.handle_password("secret pass")

        self.assertEqual(duplicate.state, "COMMAND")
        self.assertEqual(first.state, "DISCONNECTED")
        self.assertNotIn(first, veilborn_mud.players_in_rooms.get(first.location_key, []))
        self.assertIn("Another connection has taken over this character.", first.messages)
        self.assertIn(duplicate, veilborn_mud.players_in_rooms[duplicate.location_key])

    def test_stat_allocation_rejects_invalid_values(self):
        player = TestProtocol(veilborn_mud.cursor)
        player.handle_username("StatUser")
        player.register_password("password")
        player.confirm_password("password")
        player.choose_specialty("1")
        player.choose_clan("1")
        player.choose_essence("5")

        player.allocate_stats("strength=-1 dexterity=2 agility=2 intelligence=2 wisdom=5")
        self.assertEqual(player.state, "ALLOCATE_STATS")

        player.allocate_stats("strength=2 dexterity=2 agility=2 intelligence=2")
        self.assertEqual(player.state, "ALLOCATE_STATS")

        player.allocate_stats("strength=11 dexterity=0 agility=0 intelligence=0 wisdom=0")
        self.assertEqual(player.state, "ALLOCATE_STATS")

    def test_password_input_is_redacted_in_logs(self):
        player = TestProtocol(veilborn_mud.cursor)
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
                wisp INTEGER
            )
            """
        )
        connection.execute(
            """
            INSERT INTO players (username, password, health, stamina, wisp)
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
        self.assertEqual(player["max_wisp"], 21)
        self.assertEqual(player["clan"], "Unaffiliated")
        self.assertEqual(player["essence"], "Undeclared")
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


class PlayerAdminTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.players_in_rooms.clear()
        self.connection.execute(
            """
            INSERT INTO players (
                username, password, is_admin, is_builder, role_type, clan, essence,
                house_alignment, health, max_health, stamina, max_stamina,
                wisp, max_wisp, nutrition, hydration, fatigue
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Target",
                "secret-hash",
                0,
                0,
                "Veilcraft",
                "Moonveil",
                "Unimbued",
                "None",
                10,
                10,
                10,
                10,
                10,
                10,
                100,
                100,
                0,
            ),
        )
        self.connection.execute(
            """
            INSERT INTO players (
                username, password, is_admin, is_builder, role_type, clan, essence,
                x, y, last_login_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("BuilderTarget", "builder-secret", 0, 1, "Bodycraft", "Ashwake", "Feline", 501, 500, "2026-06-03 12:00:00"),
        )
        self.connection.execute(
            """
            INSERT INTO skill_definitions (skill_key, name, description, usage_gain, is_available)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("throw", "Throw", "Throwing weapons.", 1, 1),
        )
        self.connection.execute(
            """
            INSERT INTO expression_definitions (expression_key, name, description, usage_gain, is_available)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("substitution-technique", "Substitution Expression", "Body replacement.", 1, 1),
        )
        target_id = self.connection.execute(
            "SELECT id FROM players WHERE username='Target'"
        ).fetchone()["id"]
        skill_id = self.connection.execute(
            "SELECT id FROM skill_definitions WHERE skill_key='throw'"
        ).fetchone()["id"]
        expression_id = self.connection.execute(
            "SELECT id FROM expression_definitions WHERE expression_key='substitution-technique'"
        ).fetchone()["id"]
        self.connection.execute(
            """
            INSERT INTO character_skills (player_id, skill_definition_id, progress_percent, progress_points)
            VALUES (?, ?, ?, ?)
            """,
            (target_id, skill_id, 25, 250),
        )
        self.connection.execute(
            """
            INSERT INTO character_expressions (player_id, expression_definition_id, progress_percent, progress_points)
            VALUES (?, ?, ?, ?)
            """,
            (target_id, expression_id, 5, 50),
        )
        self.connection.commit()
        self.admin = TestProtocol(self.connection.cursor())
        self.admin.username = "Admin"
        self.admin.is_admin = True

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        self.connection.close()

    def test_pstat_displays_player_state_without_password(self):
        admin_commands.pstat(self.admin, "Target")

        rendered = "\n".join(self.admin.messages)
        self.assertIn("Player Target (id ", rendered)
        self.assertIn("Admin: no  Builder: no", rendered)
        self.assertIn("Online: no", rendered)
        self.assertIn("Specialty: Veilcraft  Clan: Moonveil  Essence: Unimbued", rendered)
        self.assertIn("Created:", rendered)
        self.assertIn("Last Login:", rendered)
        self.assertIn("Body: nutrition=100 hydration=100 fatigue=0", rendered)
        self.assertIn("Stance: S3 - Balance", rendered)
        self.assertIn("Skills:", rendered)
        self.assertIn("Throw: Novice (250 pts, 16%, available)", rendered)
        self.assertIn("Expressions:", rendered)
        self.assertIn("Substitution Expression: Unlearned (50 pts, 43%, available)", rendered)
        self.assertIn("Manage: pedit/pset <username> <field> <value>", rendered)
        self.assertNotIn("secret-hash", rendered)

    def test_players_lists_registered_accounts_for_admin_management(self):
        online_target = TestProtocol(self.connection.cursor())
        online_target.username = "Target"
        online_target.x = 500
        online_target.y = 500
        online_target.track_player()

        admin_commands.players(self.admin)

        rendered = "\n".join(self.admin.messages)
        self.assertIn("Registered players: 2", rendered)
        self.assertIn("Target [online; player]", rendered)
        self.assertIn("BuilderTarget [offline; builder]", rendered)
        self.assertIn("last_login=2026-06-03 12:00:00", rendered)
        self.assertIn("Use finger <username> to inspect; use pedit/pset", rendered)
        self.assertNotIn("secret-hash", rendered)
        self.assertNotIn("builder-secret", rendered)

    def test_pset_updates_validated_fields_and_clamps_current_resource(self):
        admin_commands.pset(self.admin, "Target", "health", "9")
        admin_commands.pset(self.admin, "Target", "maxhealth", "5")
        admin_commands.pset(self.admin, "Target", "nutrition", "75")

        player = self.connection.execute(
            "SELECT health, max_health, nutrition FROM players WHERE username='Target'"
        ).fetchone()
        self.assertEqual(tuple(player), (5, 5, 75))

    def test_pset_rejects_missing_players_unknown_fields_and_body_overflow(self):
        admin_commands.pset(self.admin, "Missing", "health", "9")
        admin_commands.pset(self.admin, "Target", "password", "visible")
        admin_commands.pset(self.admin, "Target", "fatigue", "101")
        admin_commands.pset(self.admin, "Target", "wisp", "11")

        self.assertIn("Player not found: Missing", self.admin.messages)
        self.assertIn("Unable to set player: Player field must be", self.admin.messages[-3])
        self.assertEqual(self.admin.messages[-2], "Unable to set player: fatigue must be between 0 and 100.")
        self.assertEqual(self.admin.messages[-1], "Unable to set player: wisp cannot exceed max_wisp (10).")

    def test_pset_refreshes_connected_admin_and_specialty_metadata(self):
        target = TestProtocol(self.connection.cursor())
        target.username = "Target"
        target.x = 500
        target.y = 500
        target.is_admin = False
        target.is_builder = False
        target.player_class = "Veilcraft"
        target.track_player()

        admin_commands.pset(self.admin, "Target", "admin", "on")
        admin_commands.pedit(self.admin, "Target", "builder", "on")
        admin_commands.pset(self.admin, "Target", "specialty", "Bodycraft")

        self.assertTrue(target.is_admin)
        self.assertTrue(target.is_builder)
        self.assertEqual(target.player_class, "Bodycraft")

    def test_pedit_promotes_builder_without_admin_access(self):
        admin_commands.pedit(self.admin, "Target", "builder", "on")

        player = self.connection.execute(
            "SELECT is_admin, is_builder FROM players WHERE username='Target'"
        ).fetchone()
        self.assertEqual(tuple(player), (0, 1))
        self.assertEqual(self.admin.messages[-1], "Set is_builder of Target to 1.")


if __name__ == "__main__":
    unittest.main()
