import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import general_commands
import shinobi_mud
import utils
from combat import (
    combat_status,
    engage_npc,
    queue_combat_modifier,
    set_stance,
    tick_combat,
)
from content import sync_authored_content
from migrations import (
    apply_migrations,
    migration_014_pulse_combat_engagements,
    migration_015_stance_profiles,
)
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PulseCombatTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.players_in_rooms.clear()
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
            """
            INSERT INTO players (username, password, x, y, health, strength)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Fighter", "hash", 500, 499, 10, 10),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "Fighter"
        self.player.x = 500
        self.player.y = 499
        self.player.state = "COMMAND"

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def make_due(self):
        self.connection.execute(
            "UPDATE combat_engagements SET next_pulse_at=datetime('now', '-1 second')"
        )
        self.connection.commit()

    def test_attack_command_engages_without_immediate_damage(self):
        general_commands.handle_attack(self.player, "practice")

        npc_health = self.connection.execute(
            """
            SELECT health FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.npc_key='practice-construct'
            """
        ).fetchone()["health"]
        self.assertEqual(npc_health, 12)
        self.assertEqual(
            self.player.messages,
            ["You engage Practice Construct. Basic auto attacks pulse every 6 seconds while you are in range."],
        )
        self.assertEqual(combat_status(self.player.cursor, "Fighter")["distance"], 0)

    def test_due_pulse_resolves_auto_attack_and_counterattack(self):
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[1, 1]):
            events = tick_combat(self.connection)

        self.assertEqual(events[0]["status"], "exchange")
        self.assertEqual((events[0]["player_damage"], events[0]["npc_health"]), (5, 7))
        self.assertEqual(events[0]["player_health"], 8)
        fatigue = self.connection.execute(
            "SELECT fatigue FROM players WHERE username='Fighter'"
        ).fetchone()["fatigue"]
        self.assertEqual(fatigue, 1)

    def test_movement_range_does_not_end_engagement(self):
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.connection.execute("UPDATE players SET y=500 WHERE username='Fighter'")
        self.connection.commit()
        self.make_due()

        events = tick_combat(self.connection)

        self.assertEqual(events[0]["status"], "out_of_range")
        self.assertEqual(events[0]["distance"], 1)
        self.assertIsNotNone(combat_status(self.player.cursor, "Fighter")["npc_name"])

    def test_queued_range_modifier_reaches_mid_range_once(self):
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.connection.execute("UPDATE players SET y=500 WHERE username='Fighter'")
        self.connection.commit()
        queued = queue_combat_modifier(
            self.player.cursor,
            "Fighter",
            "test-mid-range",
            damage_bonus=2,
            max_range=1,
        )
        self.make_due()

        with patch("combat.random.randint", return_value=1):
            event = tick_combat(self.connection)[0]

        self.assertEqual(queued["status"], "queued")
        self.assertEqual((event["status"], event["player_damage"], event["npc_health"]), ("exchange", 7, 5))
        self.assertFalse(event["npc_hit"])
        self.assertIsNone(combat_status(self.player.cursor, "Fighter")["action_key"])

    def test_authored_stances_adjust_pulse_and_persist_without_engagement(self):
        stances = self.connection.execute(
            """
            SELECT stance_key, accuracy_bonus, damage_bonus,
                   evasion_bonus, damage_reduction_bonus, pulse_seconds
            FROM stance_definitions
            ORDER BY stance_key
            """
        ).fetchall()
        attack = set_stance(self.player.cursor, "Fighter", "s1")

        self.assertEqual(
            [tuple(stance) for stance in stances],
            [
                ("s1-attack", 2, -1, -1, 0, 6),
                ("s2-damage", -1, 2, -1, 0, 6),
                ("s3-balance", 0, 0, 0, 0, 6),
                ("s4-evasion", -1, -1, 2, 0, 6),
                ("s5-damage-reduction", -1, -1, 0, 2, 6),
            ],
        )
        self.assertEqual((attack["accuracy_bonus"], attack["evasion_bonus"]), (2, -1))
        self.assertEqual(combat_status(self.player.cursor, "Fighter")["stance_name"], "S1 - Attack")
        general_commands.handle_stance(self.player, "s5")
        self.assertIn("damage reduction +2", self.player.messages[-1])

    def test_s1_attack_stance_turns_near_miss_into_reduced_damage_hit(self):
        set_stance(self.player.cursor, "Fighter", "s1")
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[55, 100]):
            event = tick_combat(self.connection)[0]

        self.assertTrue(event["player_hit"])
        self.assertEqual((event["player_damage"], event["npc_health"]), (4, 8))

    def test_s2_damage_stance_increases_outgoing_damage(self):
        set_stance(self.player.cursor, "Fighter", "s2")
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[1, 100]):
            event = tick_combat(self.connection)[0]

        self.assertEqual((event["player_damage"], event["npc_health"]), (7, 5))

    def test_s4_evasion_stance_turns_near_hit_into_miss(self):
        set_stance(self.player.cursor, "Fighter", "s4")
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[100, 45]):
            event = tick_combat(self.connection)[0]

        self.assertFalse(event["npc_hit"])
        self.assertEqual(event["player_health"], 10)

    def test_s5_damage_reduction_stance_absorbs_incoming_damage(self):
        set_stance(self.player.cursor, "Fighter", "s5")
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[100, 1]):
            event = tick_combat(self.connection)[0]

        self.assertTrue(event["npc_hit"])
        self.assertEqual((event["npc_damage"], event["player_health"]), (0, 10))

    def test_combat_command_displays_stance_damage_reduction(self):
        set_stance(self.player.cursor, "Fighter", "s5")

        general_commands.handle_combat(self.player)

        self.assertIn("Damage reduction: +2", self.player.messages[1])

    def test_substitution_resolves_on_hostile_pulse(self):
        general_commands.handle_usejutsu(self.player, "sub")
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[100, 1]):
            event = tick_combat(self.connection)[0]

        self.assertIsNotNone(event["substitution"])
        self.assertEqual(event["player_health"], 10)
        self.assertEqual(event["substitution"]["progress_percent"], 1)

    def test_runtime_tick_delivers_pulse_feedback_to_online_player(self):
        self.player.track_player()
        general_commands.handle_attack(self.player, "practice")
        self.player.messages.clear()
        self.make_due()

        with patch("combat.random.randint", side_effect=[1, 1]):
            shinobi_mud.run_combat_tick()

        self.assertEqual(
            self.player.messages,
            [
                "You strike Practice Construct for 5 damage. Practice Construct has 7 health remaining.",
                "Practice Construct strikes you for 2 damage. You have 8 health remaining.",
            ],
        )

    def test_two_due_players_apply_damage_to_shared_npc_without_lost_updates(self):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y, health, strength)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Teammate", "hash", 500, 499, 10, 10),
        )
        self.connection.commit()
        engage_npc(self.player.cursor, "Fighter", 500, 499, "practice")
        engage_npc(self.player.cursor, "Teammate", 500, 499, "practice")
        self.make_due()

        with patch("combat.random.randint", side_effect=[1, 100, 1, 100]):
            events = tick_combat(self.connection)

        self.assertEqual(len(events), 2)
        health = self.connection.execute(
            """
            SELECT health FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.npc_key='practice-construct'
            """
        ).fetchone()["health"]
        self.assertEqual(health, 2)

    def test_migration_14_preserves_existing_player_rows(self):
        connection = sqlite3.connect(":memory:")
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE players (id INTEGER PRIMARY KEY, username TEXT)")
        cursor.execute("CREATE TABLE npc_instances (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO players (id, username) VALUES (1, 'Existing')")

        migration_014_pulse_combat_engagements(cursor)

        self.assertEqual(cursor.execute("SELECT username FROM players").fetchone()[0], "Existing")
        tables = {
            row[0]
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertIn("combat_engagements", tables)
        connection.close()

    def test_migration_15_adds_damage_reduction_and_retires_initial_placeholders(self):
        connection = sqlite3.connect(":memory:")
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE players (id INTEGER PRIMARY KEY, username TEXT)")
        cursor.execute("CREATE TABLE npc_instances (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO players (id, username) VALUES (1, 'Existing')")
        cursor.execute(
            """
            CREATE TABLE stance_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stance_key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                description TEXT NOT NULL,
                accuracy_bonus INTEGER NOT NULL DEFAULT 0,
                evasion_bonus INTEGER NOT NULL DEFAULT 0,
                damage_bonus INTEGER NOT NULL DEFAULT 0,
                pulse_seconds INTEGER NOT NULL DEFAULT 6
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE character_stances (
                player_id INTEGER PRIMARY KEY,
                stance_definition_id INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO stance_definitions (
                stance_key, name, description, accuracy_bonus,
                evasion_bonus, damage_bonus, pulse_seconds
            )
            VALUES ('mongoose', 'Mongoose Stance', 'retired', 1, -1, 0, 4)
            """
        )
        stance_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO character_stances (player_id, stance_definition_id) VALUES (1, ?)",
            (stance_id,),
        )

        migration_015_stance_profiles(cursor)

        columns = {
            column[1]: column[4]
            for column in cursor.execute("PRAGMA table_info(stance_definitions)")
        }
        self.assertEqual(columns["damage_reduction_bonus"], "0")
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM stance_definitions").fetchone()[0], 0)
        self.assertEqual(cursor.execute("SELECT COUNT(*) FROM character_stances").fetchone()[0], 0)
        connection.close()


if __name__ == "__main__":
    unittest.main()
