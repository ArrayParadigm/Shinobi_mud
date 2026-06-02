import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from migrations import apply_migrations, migration_006_combat_reliability
from npcs import attack_npc, npcs_at, throw_item_at_npc, tick_npcs
from items import inventory_items, room_items
from techniques import activate_jutsu
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CombatSliceTests(unittest.TestCase):
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
            ("Fighter", shinobi_mud.hash_password("password"), 500, 499, 10, 10),
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

    def test_attack_uses_strength_damage_and_enemy_counterattack(self):
        with patch("npcs.random.randint", side_effect=[1, 1]):
            general_commands.handle_attack(self.player, "practice construct")

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name=?
            """,
            ("Practice Construct",),
        ).fetchone()["health"]
        player = self.connection.execute(
            "SELECT health, fatigue FROM players WHERE username=?",
            ("Fighter",),
        ).fetchone()

        self.assertEqual(npc_health, 7)
        self.assertEqual(player["health"], 8)
        self.assertEqual(player["fatigue"], 5)
        self.assertEqual(
            self.player.messages,
            [
                "You strike Practice Construct for 5 damage. Practice Construct has 7 health remaining.",
                "Practice Construct strikes you for 2 damage. You have 8 health remaining.",
            ],
        )

    def test_defeated_enemy_hides_until_world_tick_respawns_it(self):
        self.connection.execute(
            """
            UPDATE npc_instances
            SET health=4
            WHERE npc_template_id=(
                SELECT id FROM npc_templates WHERE name=?
            )
            """,
            ("Practice Construct",),
        )
        self.connection.commit()

        with patch("npcs.random.randint", return_value=1):
            general_commands.handle_attack(self.player, "Practice Construct")

        self.assertEqual(npcs_at(self.player.cursor, 500, 499), [])
        self.connection.execute(
            """
            UPDATE npc_instances
            SET defeated_at=datetime('now', '-61 seconds')
            WHERE npc_template_id=(
                SELECT id FROM npc_templates WHERE name=?
            )
            """,
            ("Practice Construct",),
        )
        self.connection.commit()

        tick_npcs(self.connection)

        respawned = npcs_at(self.player.cursor, 500, 499)
        self.assertEqual([npc["name"] for npc in respawned], ["Practice Construct"])
        health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name=?
            """,
            ("Practice Construct",),
        ).fetchone()["health"]
        self.assertEqual(health, 12)

    def test_attack_rejects_protected_and_missing_targets(self):
        self.player.x = 500
        self.player.y = 500

        general_commands.handle_attack(self.player, "Haven Guide")
        general_commands.handle_attack(self.player, "Missing Character")

        self.assertEqual(
            self.player.messages,
            [
                "Haven Guide is not a combat target.",
                "You do not see that character here.",
            ],
        )

    def test_player_defeat_recovers_health(self):
        self.connection.execute(
            "UPDATE players SET health=1, max_health=15 WHERE username=?",
            ("Fighter",),
        )
        self.connection.commit()

        with patch("npcs.random.randint", side_effect=[1, 1]):
            general_commands.handle_attack(self.player, "Practice Construct")

        health = self.connection.execute(
            "SELECT health FROM players WHERE username=?",
            ("Fighter",),
        ).fetchone()["health"]
        self.assertEqual(health, 15)
        self.assertEqual((self.player.x, self.player.y), (500, 499))
        self.assertEqual(
            self.player.messages[-1],
            "Practice Construct strikes you for 2 damage. You are defeated, then recover here with 15 health.",
        )

    def test_substitution_prevents_landing_npc_strike_and_records_jutsu_use(self):
        activate_jutsu(self.player.cursor, "Fighter", "sub")
        self.player.messages.clear()

        with patch("npcs.random.randint", side_effect=[100, 1]):
            general_commands.handle_attack(self.player, "Practice Construct")

        player = self.connection.execute(
            "SELECT health, chakra FROM players WHERE username='Fighter'"
        ).fetchone()
        progress = self.connection.execute(
            """
            SELECT progress_percent
            FROM character_jutsus
            JOIN players ON players.id=character_jutsus.player_id
            JOIN jutsu_definitions ON jutsu_definitions.id=character_jutsus.jutsu_definition_id
            WHERE players.username='Fighter'
              AND jutsu_definitions.jutsu_key='substitution-technique'
            """
        ).fetchone()["progress_percent"]

        self.assertEqual((player["health"], player["chakra"]), (10, 7))
        self.assertEqual(progress, 1)
        self.assertEqual(
            activate_jutsu(self.player.cursor, "Fighter", "sub")["status"],
            "cooldown",
        )
        self.assertEqual(
            self.player.messages,
            [
                "You attack Practice Construct, but miss.",
                "You evade Practice Construct through Substitution Technique. Jutsu: Novice (1%).",
            ],
        )

    def test_substitution_progression_failure_rolls_back_combat_turn(self):
        activate_jutsu(self.player.cursor, "Fighter", "sub")
        self.connection.execute(
            """
            CREATE TRIGGER reject_substitution_progress
            BEFORE INSERT ON character_jutsus
            BEGIN
                SELECT RAISE(ABORT, 'blocked substitution progress');
            END
            """
        )
        self.connection.commit()

        with patch("npcs.random.randint", side_effect=[1, 1]):
            with self.assertRaises(sqlite3.IntegrityError):
                attack_npc(self.player.cursor, "Fighter", 500, 499, "Practice Construct")

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name='Practice Construct'
            """
        ).fetchone()["health"]
        state = self.connection.execute(
            "SELECT active_until FROM character_jutsu_states"
        ).fetchone()["active_until"]
        self.assertEqual(npc_health, 12)
        self.assertIsNotNone(state)

    def test_damage_persists_across_disconnect_and_reconnect(self):
        self.player.track_player()
        with patch("npcs.random.randint", side_effect=[1, 1]):
            general_commands.handle_attack(self.player, "Practice Construct")
        self.player.connectionLost("test disconnect")

        returning_player = TestProtocol(shinobi_mud.cursor)
        returning_player.handle_username("Fighter")
        returning_player.handle_password("password")

        self.assertEqual(
            self.connection.execute(
                "SELECT health FROM players WHERE username=?",
                ("Fighter",),
            ).fetchone()["health"],
            8,
        )
        self.assertIn("[HP:8/10 ST:10/10 CH:10/10 | Eve's Haven [3001] (500, 499)]", returning_player.messages)

    def test_attack_can_miss_on_both_sides_without_changing_health(self):
        with patch("npcs.random.randint", side_effect=[100, 100]):
            general_commands.handle_attack(self.player, "Practice Construct")

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name=?
            """,
            ("Practice Construct",),
        ).fetchone()["health"]
        player_health = self.connection.execute(
            "SELECT health FROM players WHERE username=?",
            ("Fighter",),
        ).fetchone()["health"]
        self.assertEqual((npc_health, player_health), (12, 10))
        self.assertEqual(
            self.player.messages,
            [
                "You attack Practice Construct, but miss.",
                "Practice Construct attacks you, but misses.",
            ],
        )

    def test_equipped_weapon_metadata_adds_basic_attack_damage(self):
        general_commands.handle_get(self.player, "kun")
        general_commands.handle_wield(self.player, "kun")
        self.player.messages.clear()

        with patch("npcs.random.randint", side_effect=[1, 1]):
            general_commands.handle_attack(self.player, "Practice Construct")

        self.assertEqual(
            self.player.messages[0],
            "You strike Practice Construct for 6 damage. Practice Construct has 6 health remaining.",
        )

    def test_throw_hits_adjacent_target_lands_item_and_records_proficiency(self):
        general_commands.handle_get(self.player, "kun")
        self.player.x = 500
        self.player.y = 500
        self.player.messages.clear()

        with patch("npcs.random.randint", return_value=1):
            general_commands.handle_throw(self.player, "Practice Kunai at Practice Construct")

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name='Practice Construct'
            """
        ).fetchone()["health"]
        progress = self.connection.execute(
            """
            SELECT progress_percent
            FROM character_skills
            JOIN players ON players.id=character_skills.player_id
            JOIN skill_definitions ON skill_definitions.id=character_skills.skill_definition_id
            WHERE players.username='Fighter' AND skill_definitions.skill_key='throw'
            """
        ).fetchone()["progress_percent"]
        fatigue = self.connection.execute(
            "SELECT fatigue FROM players WHERE username='Fighter'"
        ).fetchone()["fatigue"]

        self.assertEqual(npc_health, 9)
        self.assertEqual(progress, 1)
        self.assertEqual(fatigue, 2)
        self.assertEqual(inventory_items(self.player.cursor, "Fighter"), [])
        self.assertEqual(
            [item["name"] for item in room_items(self.player.cursor, 500, 499)],
            ["Practice Kunai"],
        )
        self.assertEqual(
            self.player.messages,
            [
                "You throw Practice Kunai at Practice Construct for 3 damage. "
                "Practice Construct has 9 health remaining. Throw: Novice (1%)."
            ],
        )

    def test_throw_miss_still_lands_item_and_records_valid_use(self):
        general_commands.handle_get(self.player, "kun")
        self.player.messages.clear()

        with patch("npcs.random.randint", return_value=100):
            general_commands.handle_throw(self.player, "kun AT practice")

        self.assertEqual(
            self.player.messages,
            ["You throw Practice Kunai at Practice Construct, but miss. Throw: Novice (1%)."],
        )
        self.assertEqual(inventory_items(self.player.cursor, "Fighter"), [])

    def test_throw_rejects_target_outside_cardinal_range_without_losing_item(self):
        general_commands.handle_get(self.player, "kun")
        self.player.x = 500
        self.player.y = 501
        self.player.messages.clear()

        general_commands.handle_throw(self.player, "kun at practice")

        self.assertEqual(
            self.player.messages,
            ["You do not see that character within throwing range."],
        )
        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Fighter")],
            ["Practice Kunai"],
        )

    def test_throw_rejects_non_throwable_carried_item_without_losing_it(self):
        self.player.x = 500
        self.player.y = 500
        general_commands.handle_get(self.player, "map")
        self.player.x = 500
        self.player.y = 499
        self.player.messages.clear()

        general_commands.handle_throw(self.player, "map at practice")

        self.assertEqual(self.player.messages, ["Haven Map is not throwable."])
        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Fighter")],
            ["Haven Map"],
        )

    def test_throw_progression_failure_rolls_back_item_and_npc_damage(self):
        general_commands.handle_get(self.player, "kun")
        self.connection.execute(
            """
            CREATE TRIGGER reject_throw_progress
            BEFORE INSERT ON character_skills
            BEGIN
                SELECT RAISE(ABORT, 'blocked throw progress');
            END
            """
        )
        self.connection.commit()

        with patch("npcs.random.randint", return_value=1):
            with self.assertRaises(sqlite3.IntegrityError):
                throw_item_at_npc(
                    self.player.cursor,
                    "Fighter",
                    500,
                    499,
                    "kun",
                    "practice",
                )

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name='Practice Construct'
            """
        ).fetchone()["health"]
        self.assertEqual(npc_health, 12)
        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Fighter")],
            ["Practice Kunai"],
        )

    def test_consider_displays_current_and_maximum_npc_health(self):
        general_commands.handle_consider(self.player, "Practice Construct")

        self.assertEqual(
            self.player.messages,
            [
                "Practice Construct",
                "A training construct waits for a sparring partner among the luminous flora.",
                "Health: 12/12",
                "Attack: 2  Accuracy: 5  Evasion: 5",
            ],
        )

    def test_combat_exchange_is_broadcast_to_roommates(self):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y)
            VALUES (?, ?, ?, ?)
            """,
            ("Observer", "hash", 500, 499),
        )
        self.connection.commit()
        observer = TestProtocol(shinobi_mud.cursor)
        observer.username = "Observer"
        observer.x = 500
        observer.y = 499
        observer.track_player()
        observer.messages.clear()

        with patch("npcs.random.randint", side_effect=[1, 1]):
            general_commands.handle_attack(self.player, "Practice Construct")

        self.assertEqual(
            observer.messages,
            [
                "Fighter strikes Practice Construct for 5 damage. Practice Construct has 7 health remaining.",
                "Practice Construct strikes Fighter for 2 damage. Fighter has 8 health remaining.",
            ],
        )

    def test_two_players_damage_the_same_npc_without_losing_updates(self):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y, strength)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Teammate", "hash", 500, 499, 10),
        )
        self.connection.commit()
        teammate = TestProtocol(shinobi_mud.cursor)
        teammate.username = "Teammate"
        teammate.x = 500
        teammate.y = 499

        with patch("npcs.random.randint", side_effect=[1, 100, 1, 100]):
            general_commands.handle_attack(self.player, "Practice Construct")
            general_commands.handle_attack(teammate, "Practice Construct")

        npc_health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name=?
            """,
            ("Practice Construct",),
        ).fetchone()["health"]
        self.assertEqual(npc_health, 2)

    def test_failed_combat_turn_rolls_back_npc_damage(self):
        self.connection.execute(
            """
            CREATE TRIGGER reject_player_health_update
            BEFORE UPDATE OF health ON players
            BEGIN
                SELECT RAISE(ABORT, 'blocked health update');
            END
            """
        )
        self.connection.commit()

        with patch("npcs.random.randint", side_effect=[1, 1]):
            with self.assertRaises(sqlite3.IntegrityError):
                attack_npc(self.player.cursor, "Fighter", 500, 499, "Practice Construct")

        health = self.connection.execute(
            """
            SELECT health
            FROM npc_instances
            JOIN npc_templates ON npc_templates.id=npc_instances.npc_template_id
            WHERE npc_templates.name=?
            """,
            ("Practice Construct",),
        ).fetchone()["health"]
        self.assertEqual(health, 12)

    def test_combat_reliability_migration_upgrades_existing_npc_templates(self):
        connection = sqlite3.connect(":memory:")
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE npc_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                description TEXT NOT NULL,
                dialogue TEXT NOT NULL,
                behavior TEXT NOT NULL DEFAULT 'static',
                max_health INTEGER NOT NULL DEFAULT 1,
                attack_damage INTEGER NOT NULL DEFAULT 0,
                respawn_seconds INTEGER NOT NULL DEFAULT 60
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE npc_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_template_id INTEGER NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                home_x INTEGER NOT NULL,
                home_y INTEGER NOT NULL,
                seed_key TEXT UNIQUE,
                last_tick_at TEXT,
                health INTEGER NOT NULL DEFAULT 1,
                defeated_at TEXT
            )
            """
        )

        migration_006_combat_reliability(cursor)

        columns = {
            column[1]: column[4]
            for column in cursor.execute("PRAGMA table_info(npc_templates)")
        }
        self.assertEqual(columns["accuracy"], "5")
        self.assertEqual(columns["evasion"], "5")
        connection.close()


if __name__ == "__main__":
    unittest.main()
