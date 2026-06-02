import sqlite3
import unittest
from pathlib import Path

import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from migrations import apply_migrations, migration_009_skill_and_jutsu_framework
from techniques import list_jutsus, list_skills, practice_skill, train_jutsu
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TechniqueFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.WORLD_OVERLAYS.clear()
        utils.preload_zones_with_anchors(
            shinobi_mud.WORLD_OVERLAYS,
            str(PROJECT_ROOT / "zones"),
        )
        sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            shinobi_mud.WORLD_OVERLAYS,
        )
        self.connection.execute(
            "INSERT INTO players (username, password) VALUES (?, ?)",
            ("Student", "hash"),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "Student"

    def tearDown(self):
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_authored_framework_syncs_throw_and_substitution_separately(self):
        skills = list_skills(self.player.cursor, "Student")
        jutsus = list_jutsus(self.player.cursor, "Student")

        self.assertEqual(
            [(row["name"], row["rank"], row["points"]) for row in skills],
            [("Throw", 0, 5)],
        )
        self.assertEqual(
            [(row["name"], row["rank"], row["points"]) for row in jutsus],
            [("Substitution Technique", 0, 5)],
        )

    def test_prac_and_train_list_available_progress(self):
        general_commands.handle_progression(self.player, "", "skill")
        general_commands.handle_progression(self.player, "", "jutsu")

        self.assertEqual(
            self.player.messages,
            [
                "Skills",
                "Practice points: 5",
                "  Throw: 0/100",
                "Jutsus",
                "Training points: 5",
                "  Substitution Technique: 0/100",
            ],
        )

    def test_prac_and_train_advance_separate_persistent_progress(self):
        general_commands.handle_progression(self.player, "thr", "skill")
        general_commands.handle_progression(self.player, "sub", "jutsu")
        returning_player = TestProtocol(self.connection.cursor())
        returning_player.username = "Student"

        general_commands.handle_progression(returning_player, "", "skill")
        general_commands.handle_progression(returning_player, "", "jutsu")

        self.assertEqual(
            self.player.messages,
            [
                "You practice Throw. Rank: 1. Practice points: 4.",
                "You train Substitution Technique. Rank: 1. Training points: 4.",
            ],
        )
        self.assertEqual(
            returning_player.messages,
            [
                "Skills",
                "Practice points: 4",
                "  Throw: 1/100",
                "Jutsus",
                "Training points: 4",
                "  Substitution Technique: 1/100",
            ],
        )

    def test_advancement_rejects_invalid_targets_caps_and_missing_points(self):
        self.assertEqual(practice_skill(self.player.cursor, "Student", "missing")["status"], "missing")
        self.connection.execute(
            "UPDATE skill_definitions SET max_rank=1 WHERE skill_key='throw'"
        )
        self.connection.commit()
        self.assertEqual(practice_skill(self.player.cursor, "Student", "throw")["status"], "advanced")
        self.assertEqual(practice_skill(self.player.cursor, "Student", "throw")["status"], "capped")
        self.connection.execute(
            "UPDATE players SET training_points=0 WHERE username='Student'"
        )
        self.connection.commit()
        self.assertEqual(
            train_jutsu(self.player.cursor, "Student", "substitution")["status"],
            "insufficient",
        )

    def test_framework_migration_preserves_existing_players(self):
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
            ("LegacyStudent", "hash"),
        )

        migration_009_skill_and_jutsu_framework(connection.cursor())

        player = connection.execute(
            "SELECT username, practice_points, training_points FROM players"
        ).fetchone()
        self.assertEqual(tuple(player), ("LegacyStudent", 5, 5))
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertTrue(
            {"skill_definitions", "jutsu_definitions", "character_skills", "character_jutsus"}
            <= tables
        )
        connection.close()


if __name__ == "__main__":
    unittest.main()
