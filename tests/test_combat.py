import sqlite3
import unittest
from pathlib import Path

import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from migrations import apply_migrations
from npcs import npcs_at, tick_npcs
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
        player_health = self.connection.execute(
            "SELECT health FROM players WHERE username=?",
            ("Fighter",),
        ).fetchone()["health"]

        self.assertEqual(npc_health, 7)
        self.assertEqual(player_health, 8)
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
            "UPDATE players SET health=1 WHERE username=?",
            ("Fighter",),
        )
        self.connection.commit()

        general_commands.handle_attack(self.player, "Practice Construct")

        health = self.connection.execute(
            "SELECT health FROM players WHERE username=?",
            ("Fighter",),
        ).fetchone()["health"]
        self.assertEqual(health, 10)
        self.assertEqual(
            self.player.messages[-1],
            "Practice Construct strikes you for 2 damage. You are defeated, then recover with 10 health.",
        )

    def test_damage_persists_across_disconnect_and_reconnect(self):
        self.player.track_player()
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
        self.assertIn("[HP:8 ST:10 CH:10 | Eve's Haven [3001] (500, 499)]", returning_player.messages)


if __name__ == "__main__":
    unittest.main()
