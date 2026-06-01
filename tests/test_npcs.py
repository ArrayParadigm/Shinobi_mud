import sqlite3
import unittest
from pathlib import Path

from twisted.internet import task

import admin_commands
import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from migrations import apply_migrations
from npcs import npcs_at
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NPCFoundationTests(unittest.TestCase):
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
            INSERT INTO players (username, password, x, y, is_admin)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Visitor", "hash", 500, 500, 1),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "Visitor"
        self.player.x = 500
        self.player.y = 500
        self.player.is_admin = True

    def tearDown(self):
        if shinobi_mud.WORLD_TICK_LOOP and shinobi_mud.WORLD_TICK_LOOP.running:
            shinobi_mud.WORLD_TICK_LOOP.stop()
        shinobi_mud.WORLD_TICK_LOOP = None
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_authored_npc_spawn_survives_content_reload_without_duplication(self):
        imported = sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            shinobi_mud.WORLD_OVERLAYS,
        )

        npcs = npcs_at(self.player.cursor, 500, 500)
        self.assertEqual([npc["name"] for npc in npcs], ["Haven Guide"])
        self.assertEqual(imported["npc_spawns"], 0)

    def test_room_rendering_lists_npc(self):
        utils.render_room(self.player, shinobi_mud.WORLD_OVERLAYS)

        self.assertTrue(
            any("Characters: Haven Guide" in message for message in self.player.messages)
        )

    def test_talk_returns_authored_dialogue_and_rejects_missing_npc(self):
        general_commands.handle_talk(self.player, "haven guide")
        general_commands.handle_talk(self.player, "missing guide")

        self.assertEqual(
            self.player.messages,
            [
                'Haven Guide says, "Welcome to Eve\'s Haven. The path ahead is quiet, but it is yours to explore."',
                "You do not see that character here.",
            ],
        )

    def test_admin_reloadcontent_imports_without_duplicate_spawns(self):
        admin_commands.reloadcontent(self.player)

        self.assertEqual(
            self.player.messages,
            ["Authored content reloaded. Created 0 item spawns and 0 NPC spawns."],
        )

    def test_world_tick_updates_persistent_npc_timestamp(self):
        clock = task.Clock()

        shinobi_mud.start_world_tick(clock)
        clock.advance(shinobi_mud.WORLD_TICK_INTERVAL_SECONDS)

        last_tick_at = self.connection.execute(
            "SELECT last_tick_at FROM npc_instances"
        ).fetchone()["last_tick_at"]
        self.assertIsNotNone(last_tick_at)


if __name__ == "__main__":
    unittest.main()
