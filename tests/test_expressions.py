import sqlite3
import unittest
from pathlib import Path

import general_commands
import veilborn_mud
import utils
from content import sync_authored_content
from migrations import (
    apply_migrations,
    migration_010_usage_based_techniques,
    migration_011_technique_catalog_placeholders,
)
from expressions import (
    list_expressions,
    list_skills,
    activate_expression,
    proficiency_label,
    practice_skill,
    record_expression_use,
    record_skill_use,
    train_expression,
    tick_expression_states,
)
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TechniqueFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.WORLD_OVERLAYS.clear()
        utils.preload_zones_with_anchors(
            veilborn_mud.WORLD_OVERLAYS,
            str(PROJECT_ROOT / "zones"),
        )
        sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            veilborn_mud.WORLD_OVERLAYS,
        )
        self.connection.execute(
            "INSERT INTO players (username, password) VALUES (?, ?)",
            ("Student", "hash"),
        )
        self.connection.commit()
        self.player = TestProtocol(veilborn_mud.cursor)
        self.player.username = "Student"

    def tearDown(self):
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_authored_framework_syncs_throw_and_substitution_separately(self):
        skills = list_skills(self.player.cursor, "Student")
        expressions = list_expressions(self.player.cursor, "Student")

        self.assertEqual(
            [(row["name"], row["progress_percent"]) for row in skills],
            [("Throw", 0)],
        )
        self.assertEqual(
            [(row["name"], row["progress_percent"]) for row in expressions],
            [("Substitution Expression", 0)],
        )

    def test_prac_and_train_list_and_inspect_usage_progress(self):
        general_commands.handle_progression(self.player, "", "skill")
        general_commands.handle_progression(self.player, "", "expression")
        general_commands.handle_progression(self.player, "thr", "skill")

        self.assertEqual(
            self.player.messages,
            [
                "Skills",
                "  Throw: Untrained (0%)",
                "Expressions",
                "  Substitution Expression: Untrained (0%)",
                "Throw",
                "Training for thrown kunai, shuriken, and similar ranged weapons.",
                "Proficiency: Untrained (0%)",
            ],
        )

    def test_skill_and_expression_all_include_unimplemented_catalog_placeholders(self):
        general_commands.handle_progression(self.player, "", "skill", allow_all=True)
        general_commands.handle_progression(self.player, "all", "skill", allow_all=True)
        general_commands.handle_progression(self.player, "", "expression", allow_all=True)
        general_commands.handle_progression(self.player, "all", "expression", allow_all=True)

        self.assertEqual(self.player.messages[0:2], ["Skills", "  Throw: Untrained (0%)"])
        self.assertIn("All Skills", self.player.messages)
        self.assertIn("  Wisp Control: Untrained (0%) [unimplemented]", self.player.messages)
        self.assertIn("  Stealth: Untrained (0%) [unimplemented]", self.player.messages)
        self.assertIn("Expressions", self.player.messages)
        self.assertIn("  Substitution Expression: Untrained (0%)", self.player.messages)
        self.assertIn("All Expressions", self.player.messages)
        self.assertIn("  Clone Technique: Untrained (0%) [unimplemented]", self.player.messages)

    def test_unimplemented_catalog_placeholders_cannot_record_use(self):
        self.assertEqual(
            record_skill_use(self.player.cursor, "Student", "stealth")["status"],
            "missing",
        )
        self.assertEqual(
            record_expression_use(self.player.cursor, "Student", "clone-technique")["status"],
            "missing",
        )

    def test_valid_use_records_separate_persistent_progress(self):
        record_skill_use(self.player.cursor, "Student", "throw")
        record_expression_use(self.player.cursor, "Student", "substitution-technique")
        returning_player = TestProtocol(self.connection.cursor())
        returning_player.username = "Student"

        general_commands.handle_progression(returning_player, "", "skill")
        general_commands.handle_progression(returning_player, "", "expression")

        self.assertEqual(
            returning_player.messages,
            [
                "Skills",
                "  Throw: Untrained (10%)",
                "Expressions",
                "  Substitution Expression: Untrained (10%)",
            ],
        )

    def test_practice_and_train_advance_point_progress_with_milestones(self):
        skill_result = practice_skill(self.player.cursor, "Student", "throw")
        expression_result = train_expression(self.player.cursor, "Student", "sub")

        self.assertEqual(
            (skill_result["progress_points"], skill_result["progress_percent"], skill_result["proficiency"]),
            (10, 100, "Untrained"),
        )
        self.assertEqual(
            (expression_result["progress_points"], expression_result["progress_percent"], expression_result["proficiency"]),
            (10, 100, "Untrained"),
        )

        for _ in range(9):
            skill_result = practice_skill(self.player.cursor, "Student", "throw")

        self.assertEqual(skill_result["progress_points"], 100)
        self.assertEqual(skill_result["progress_percent"], 100)
        self.assertIn("ten_percent", skill_result["milestones"])

        tier_result = practice_skill(self.player.cursor, "Student", "throw")
        self.assertEqual((tier_result["progress_points"], tier_result["proficiency"]), (110, "Novice"))
        self.assertIn("tier", tier_result["milestones"])

    def test_prac_and_train_actions_hide_backend_percentages(self):
        general_commands.handle_practice(self.player, "throw", "skill")
        general_commands.handle_practice(self.player, "substitution", "expression")

        self.assertEqual(
            self.player.messages,
            [
                "You practice Throw.",
                "You feel more confident performing Throw.",
                "Throw: Untrained",
                "You train Substitution Expression.",
                "You feel more confident performing Substitution Expression.",
                "Substitution Expression: Untrained",
            ],
        )
        self.assertNotIn("%", "\n".join(self.player.messages))

    def test_substitution_activation_spends_wisp_and_persists_cooldown(self):
        result = activate_expression(self.player.cursor, "Student", "sub")

        state = self.connection.execute(
            "SELECT active_until, cooldown_until FROM character_expression_states"
        ).fetchone()
        wisp = self.connection.execute(
            "SELECT wisp FROM players WHERE username='Student'"
        ).fetchone()["wisp"]

        self.assertEqual(result["status"], "activated")
        self.assertEqual(wisp, 7)
        self.assertIsNotNone(state["active_until"])
        self.assertIsNotNone(state["cooldown_until"])
        self.assertEqual(
            activate_expression(self.player.cursor, "Student", "sub")["status"],
            "active",
        )

    def test_substitution_activation_rejects_insufficient_wisp(self):
        self.connection.execute("UPDATE players SET wisp=2 WHERE username='Student'")
        self.connection.commit()

        result = activate_expression(self.player.cursor, "Student", "sub")

        self.assertEqual(result["status"], "insufficient_wisp")
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM character_expression_states").fetchone()[0],
            0,
        )

    def test_expression_tick_clears_expired_substitution_state(self):
        activate_expression(self.player.cursor, "Student", "sub")
        self.connection.execute(
            """
            UPDATE character_expression_states
            SET active_until=datetime('now', '-1 second'),
                cooldown_until=datetime('now', '-1 second')
            """
        )
        self.connection.commit()

        updated = tick_expression_states(self.connection)

        self.assertEqual(updated, 1)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM character_expression_states").fetchone()[0],
            0,
        )

    def test_usage_progress_caps_at_grandmaster(self):
        skill_id = self.connection.execute(
            "SELECT id FROM skill_definitions WHERE skill_key='throw'"
        ).fetchone()["id"]
        player_id = self.connection.execute(
            "SELECT id FROM players WHERE username='Student'"
        ).fetchone()["id"]
        self.connection.execute(
            """
            INSERT INTO character_skills
                (player_id, skill_definition_id, progress_percent, progress_points)
            VALUES (?, ?, ?, ?)
            """,
            (player_id, skill_id, 99, 99999),
        )
        self.connection.commit()

        first = record_skill_use(self.player.cursor, "Student", "throw")
        second = record_skill_use(self.player.cursor, "Student", "throw")

        self.assertEqual((first["progress_percent"], first["proficiency"]), (100, "Grandmaster"))
        self.assertEqual((second["progress_percent"], second["proficiency"]), (100, "Grandmaster"))

    def test_proficiency_tier_boundaries(self):
        self.assertEqual(
            [proficiency_label(value) for value in (0, 10, 11, 100, 101, 1000, 1001, 5001, 25001, 100000)],
            [
                "Untrained",
                "Untrained",
                "Unlearned",
                "Unlearned",
                "Novice",
                "Novice",
                "Adept",
                "Trained",
                "Master",
                "Grandmaster",
            ],
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
            CREATE TABLE expression_definitions (
                id INTEGER PRIMARY KEY, expression_key TEXT, name TEXT, description TEXT,
                max_rank INTEGER, training_cost INTEGER
            );
            CREATE TABLE character_skills (
                player_id INTEGER, skill_definition_id INTEGER, rank INTEGER,
                PRIMARY KEY (player_id, skill_definition_id)
            );
            CREATE TABLE character_expressions (
                player_id INTEGER, expression_definition_id INTEGER, rank INTEGER,
                PRIMARY KEY (player_id, expression_definition_id)
            );
            INSERT INTO players VALUES (1, 'LegacyStudent', 'hash');
            INSERT INTO skill_definitions VALUES (1, 'throw', 'Throw', 'Legacy throw.', 100, 1);
            INSERT INTO expression_definitions VALUES (1, 'substitution-technique', 'Substitution Expression', 'Legacy substitution.', 100, 1);
            INSERT INTO character_skills VALUES (1, 1, 42);
            INSERT INTO character_expressions VALUES (1, 1, 17);
            """
        )

        migration_010_usage_based_techniques(connection.cursor())

        skill = connection.execute("SELECT progress_percent FROM character_skills").fetchone()
        expression = connection.execute("SELECT progress_percent FROM character_expressions").fetchone()
        self.assertEqual((skill["progress_percent"], expression["progress_percent"]), (42, 17))
        connection.close()

    def test_catalog_migration_preserves_existing_definitions_as_available(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE players (id INTEGER PRIMARY KEY, username TEXT, password TEXT);
            CREATE TABLE skill_definitions (
                id INTEGER PRIMARY KEY, skill_key TEXT, name TEXT, description TEXT,
                usage_gain INTEGER
            );
            CREATE TABLE expression_definitions (
                id INTEGER PRIMARY KEY, expression_key TEXT, name TEXT, description TEXT,
                usage_gain INTEGER
            );
            CREATE TABLE character_skills (
                player_id INTEGER, skill_definition_id INTEGER, progress_percent INTEGER,
                PRIMARY KEY (player_id, skill_definition_id)
            );
            CREATE TABLE character_expressions (
                player_id INTEGER, expression_definition_id INTEGER, progress_percent INTEGER,
                PRIMARY KEY (player_id, expression_definition_id)
            );
            INSERT INTO skill_definitions VALUES (1, 'throw', 'Throw', 'Legacy throw.', 1);
            INSERT INTO expression_definitions VALUES (1, 'substitution-technique', 'Substitution Expression', 'Legacy substitution.', 1);
            """
        )

        migration_011_technique_catalog_placeholders(connection.cursor())

        skill = connection.execute("SELECT is_available FROM skill_definitions").fetchone()
        expression = connection.execute("SELECT is_available FROM expression_definitions").fetchone()
        self.assertEqual((skill["is_available"], expression["is_available"]), (1, 1))
        connection.close()


if __name__ == "__main__":
    unittest.main()
