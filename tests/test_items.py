import sqlite3
import unittest

import general_commands
import shinobi_mud
import utils
from items import inventory_items, room_items
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


class ItemPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y)
            VALUES (?, ?, ?, ?)
            """,
            ("Collector", shinobi_mud.hash_password("password"), 500, 500),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "Collector"
        self.player.x = 500
        self.player.y = 500
        self.player.state = "COMMAND"

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_migration_seeds_eves_haven_items_once(self):
        apply_migrations(self.connection)

        definitions = self.connection.execute(
            "SELECT name FROM item_definitions ORDER BY name"
        ).fetchall()
        placements = self.connection.execute(
            "SELECT x, y, seed_key FROM room_items ORDER BY seed_key"
        ).fetchall()

        self.assertEqual(
            [row["name"] for row in definitions],
            ["Crystal Token", "Haven Map", "Practice Kunai"],
        )
        self.assertEqual(len(placements), 3)
        self.assertEqual((placements[1]["x"], placements[1]["y"]), (500, 500))

    def test_room_rendering_lists_visible_items_on_open_land(self):
        utils.render_room(self.player, {})

        self.assertEqual(
            self.player.messages,
            ["You see open land around you.", "Items here: Haven Map"],
        )

    def test_get_inventory_and_drop_transfer_one_persistent_item(self):
        general_commands.handle_get(self.player, "haven map")
        general_commands.handle_inventory(self.player)
        self.player.x = 503
        self.player.y = 497
        general_commands.handle_drop(self.player, "Haven Map")

        self.assertEqual(
            self.player.messages,
            [
                "You pick up Haven Map.",
                "Inventory: Haven Map",
                "You drop Haven Map.",
            ],
        )
        self.assertEqual(inventory_items(self.player.cursor, "Collector"), [])
        dropped = room_items(self.player.cursor, 503, 497)
        self.assertEqual([item["name"] for item in dropped], ["Haven Map"])

    def test_inventory_persists_through_reconnect(self):
        general_commands.handle_get(self.player, "Haven Map")
        returning_player = TestProtocol(shinobi_mud.cursor)

        returning_player.handle_username("Collector")
        returning_player.handle_password("password")
        returning_player.messages.clear()
        general_commands.handle_inventory(returning_player)

        self.assertEqual(returning_player.messages, ["Inventory: Haven Map"])

    def test_invalid_get_and_drop_leave_storage_unchanged(self):
        general_commands.handle_get(self.player, "Missing Item")
        general_commands.handle_drop(self.player, "Missing Item")

        self.assertEqual(
            self.player.messages,
            [
                "You do not see that item here.",
                "You are not carrying that item.",
            ],
        )
        self.assertEqual(
            [item["name"] for item in room_items(self.player.cursor, 500, 500)],
            ["Haven Map"],
        )
        self.assertEqual(inventory_items(self.player.cursor, "Collector"), [])


if __name__ == "__main__":
    unittest.main()
