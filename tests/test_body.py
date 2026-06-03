import sqlite3
import unittest

import admin_commands
import general_commands
import shinobi_mud
from body import add_fatigue, body_state, chakra_recovery_amount, rest_character
from migrations import apply_migrations, migration_007_body_foundation
from tests.test_accounts import TestProtocol


class BodyFoundationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        self.connection.execute(
            """
            INSERT INTO players (
                username, password, stamina, max_stamina, chakra, max_chakra,
                nutrition, hydration, fatigue, wisdom
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("RestingUser", "hash", 2, 10, 1, 10, 80, 60, 30, 10),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "RestingUser"

    def tearDown(self):
        self.connection.close()

    def test_body_command_displays_resources_and_recovery_estimate(self):
        general_commands.handle_body(self.player)

        self.assertEqual(
            self.player.messages,
            [
                "Body",
                "Nutrition: 80/100  Hydration: 60/100  Fatigue: 30/100",
                "Recovery: ready",
                "Short-rest chakra recovery: 4",
            ],
        )

    def test_rest_recovers_resources_and_updates_body_costs(self):
        result = rest_character(self.player.cursor, "RestingUser")

        self.assertEqual(result["stamina_restored"], 4)
        self.assertEqual(result["chakra_restored"], 4)
        self.assertEqual(result["fatigue"], 20)
        self.assertEqual(result["nutrition"], 79)
        self.assertEqual(result["hydration"], 59)
        saved = body_state(self.player.cursor, "RestingUser")
        self.assertEqual((saved["stamina"], saved["chakra"]), (6, 5))

    def test_description_score_and_admin_player_stats_use_identity_fields(self):
        general_commands.handle_description(self.player, "A quiet academy student.")
        general_commands.handle_description(self.player, "")
        general_commands.handle_score(self.player)
        admin_commands.pset(self.player, "RestingUser", "intellect", "14")
        admin_commands.pset(self.player, "RestingUser", "condition", "12")
        admin_commands.pset(self.player, "RestingUser", "description", "A focused trainee.")
        admin_commands.pstat(self.player, "RestingUser")

        transcript = "\n".join(self.player.messages)
        self.assertIn("Description updated.", transcript)
        self.assertIn("Description: A quiet academy student.", transcript)
        self.assertIn("Health: 10/10", transcript)
        self.assertIn("Fatigue: ready", transcript)
        self.assertIn("Strength: 10  Intellect: 10  Dexterity: 10  Agility: 10  Condition: 10", transcript)
        self.assertIn("Set intelligence of RestingUser to 14.", transcript)
        self.assertIn("Set wisdom of RestingUser to 12.", transcript)
        self.assertIn("  Description: A focused trainee.", transcript)
        self.assertIn("  Stats: strength=10 intellect=14 dexterity=10 agility=10 condition=12", transcript)

    def test_rest_caps_resources_and_fatigue_reduces_recovery(self):
        self.connection.execute(
            """
            UPDATE players
            SET stamina=9, chakra=9, nutrition=10, hydration=10, fatigue=80
            WHERE username=?
            """,
            ("RestingUser",),
        )
        self.connection.commit()
        state = body_state(self.player.cursor, "RestingUser")

        self.assertEqual(chakra_recovery_amount(state), 1)
        result = rest_character(self.player.cursor, "RestingUser")

        self.assertEqual(result["stamina"], 10)
        self.assertEqual(result["chakra"], 10)
        self.assertEqual(result["fatigue"], 70)
        self.assertEqual(result["recovery_state"], "strained")

    def test_exertion_caps_fatigue_and_marks_strained_recovery(self):
        add_fatigue(self.player.cursor, "RestingUser", 80)
        self.connection.commit()

        state = body_state(self.player.cursor, "RestingUser")
        self.assertEqual(state["fatigue"], 100)
        self.assertEqual(state["recovery_state"], "strained")

    def test_body_migration_preserves_existing_characters(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO players (username, password) VALUES (?, ?)",
            ("LegacyBody", "hash"),
        )

        migration_007_body_foundation(connection.cursor())

        player = connection.execute(
            "SELECT nutrition, hydration, fatigue, recovery_state FROM players"
        ).fetchone()
        self.assertEqual(tuple(player), (100, 100, 0, "ready"))
        connection.close()

    def test_rest_blocks_when_nutrition_or_hydration_is_depleted(self):
        for column in ("nutrition", "hydration"):
            self.connection.execute(
                f"UPDATE players SET nutrition=50, hydration=50, {column}=0 WHERE username=?",
                ("RestingUser",),
            )
            self.connection.commit()
            general_commands.handle_rest(self.player)

        self.assertEqual(
            self.player.messages,
            [
                "You cannot rest until you restore your nutrition.",
                "You cannot rest until you restore your hydration.",
            ],
        )

    def test_body_command_warns_about_low_resources_and_strained_fatigue(self):
        self.connection.execute(
            """
            UPDATE players
            SET nutrition=20, hydration=0, fatigue=50
            WHERE username=?
            """,
            ("RestingUser",),
        )
        self.connection.commit()

        general_commands.handle_body(self.player)

        self.assertEqual(
            self.player.messages[-3:],
            [
                "Warning: Low nutrition is reducing your recovery.",
                "Warning: You are too dehydrated to recover through rest.",
                "Warning: High fatigue is straining your recovery.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
