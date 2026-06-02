import sqlite3
import unittest
from pathlib import Path

import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from migrations import apply_migrations, migration_010_usage_based_techniques
from techniques import (
    list_jutsus,
    list_skills,
    proficiency_label,
    record_jutsu_use,
    record_skill_use,
)
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
            [(row["name"], row["progress_percent"]) for row in skills],
            [("Throw", 0)],
        )
        self.assertEqual(
            [(row["name"], row["progress_percent"]) for row in jutsus],
            [("Substitution Technique", 0)],
        )

    def test_prac_and_train_list_and_inspect_usage_progress(self):
        general_commands.handle_progression(self.player, "", "skill")
        general_commands.handle_progression(self.player, "", "jutsu")
        general_commands.handle_progression(self.player, "thr", "skill")

        self.assertEqual(
            self.player.messages,
            [
                "Skills",
                "  Throw: Novice (0%)",
                "Jutsus",
                "  Substitution Technique: Novice (0%)",
                "Throw",
                "Training for thrown kunai, shuriken, and similar ranged weapons.",
                "Proficiency: Novice (0%)",
            ],
        )

    def test_valid_use_records_separate_persistent_progress(self):
        record_skill_use(self.player.cursor, "Student", "throw")
        record_jutsu_use(self.player.cursor, "Student", "substitution-technique")
        returning_player = TestProtocol(self.connection.cursor())
        returning_player.username = "Student"

        general_commands.handle_progression(returning_player, "", "skill")
        general_commands.handle_progression(returning_player, "", "jutsu")

        self.assertEqual(
            returning_player.messages,
            [
                "Skills",
                "  Throw: Novice (1%)",
                "Jutsus",
                "  Substitution Technique: Novice (1%)",
            ],
        )

    def test_usage_progress_caps_at_grandmaster(self):
        skill_id = self.connection.execute(
            "SELECT id FROM skill_definitions WHERE skill_key='throw'"
        ).fetchone()["id"]
        player_id = self.connection.execute(
            "SELECT id FROM players WHERE username='Student'"
        ).fetchone()["id"]
        self.connection.execute(
            "INSERT INTO character_skills (player_id, skill_definition_id, progress_percent) VALUES (?, ?, ?)",
            (player_id, skill_id, 99),
        )
        self.connection.commit()

        first = record_skill_use(self.player.cursor, "Student", "throw")
        second = record_skill_use(self.player.cursor, "Student", "throw")

        self.assertEqual((first["progress_percent"], first["proficiency"]), (100, "Grandmaster"))
        self.assertEqual((second["progress_percent"], second["proficiency"]), (100, "Grandmaster"))

    def test_proficiency_tier_boundaries(self):
        self.assertEqual(
            [proficiency_label(value) for value in (0, 24, 25, 49, 50, 74, 75, 99, 100)],
            ["Novice", "Novice", "Adept", "Adept", "Skilled", "Skilled", "Master", "Master", "Grandmaster"],
        )

    def test_usage_based_migration_preserves_existing_rank_progress(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE players (id INTEGER PRIMARY KEY, username TEXT, password TEXT);
            CREATE TABLE skill_definitions (
                id INTEGER PRIMARY KEY, skill_key TEXT, name TEXT, description TEXT,
                max_rank INTEGER, practice_cost INTEGER
            );
            CREATE TABLE jutsu_definitions (
                id INTEGER PRIMARY KEY, jutsu_key TEXT, name TEXT, description TEXT,
                max_rank INTEGER, training_cost INTEGER
            );
            CREATE TABLE character_skills (
                player_id INTEGER, skill_definition_id INTEGER, rank INTEGER,
                PRIMARY KEY (player_id, skill_definition_id)
            );
            CREATE TABLE character_jutsus (
                player_id INTEGER, jutsu_definition_id INTEGER, rank INTEGER,
                PRIMARY KEY (player_id, jutsu_definition_id)
            );
            INSERT INTO players VALUES (1, 'LegacyStudent', 'hash');
            INSERT INTO skill_definitions VALUES (1, 'throw', 'Throw', 'Legacy throw.', 100, 1);
            INSERT INTO jutsu_definitions VALUES (1, 'substitution-technique', 'Substitution Technique', 'Legacy substitution.', 100, 1);
            INSERT INTO character_skills VALUES (1, 1, 42);
            INSERT INTO character_jutsus VALUES (1, 1, 17);
            """
        )

        migration_010_usage_based_techniques(connection.cursor())

        skill = connection.execute("SELECT progress_percent FROM character_skills").fetchone()
        jutsu = connection.execute("SELECT progress_percent FROM character_jutsus").fetchone()
        self.assertEqual((skill["progress_percent"], jutsu["progress_percent"]), (42, 17))
        connection.close()


if __name__ == "__main__":
    unittest.main()
