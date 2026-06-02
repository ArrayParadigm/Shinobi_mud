import sqlite3
import unittest
from pathlib import Path

import general_commands
import shinobi_mud
import utils
from content import sync_authored_content
from items import inventory_items, room_items
from migrations import apply_migrations, migration_008_consumable_items
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        imported = sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            shinobi_mud.WORLD_OVERLAYS,
        )

        definitions = self.connection.execute(
            "SELECT name FROM item_definitions ORDER BY name"
        ).fetchall()
        placements = self.connection.execute(
            "SELECT x, y, seed_key FROM room_items ORDER BY seed_key"
        ).fetchall()

        self.assertEqual(
            [row["name"] for row in definitions],
            ["Crystal Token", "Haven Map", "Practice Kunai", "Travel Ration", "Water Flask"],
        )
        self.assertEqual(len(placements), 5)
        self.assertEqual((placements[1]["x"], placements[1]["y"]), (500, 500))
        self.assertEqual(imported["item_spawns"], 0)

    def test_room_rendering_lists_visible_items_on_open_land(self):
        utils.render_room(self.player, {})

        self.assertEqual(
            self.player.messages,
            [
                "Open Land\nYou see open land around you.\nItems: Haven Map, Travel Ration, Water Flask\nCharacters: Haven Guide",
            ],
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
                "Inventory",
                "  Carried: Haven Map",
                "  Equipped: None",
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

        self.assertEqual(
            returning_player.messages,
            ["Inventory", "  Carried: Haven Map", "  Equipped: None"],
        )

    def test_authored_item_does_not_respawn_after_pickup_and_content_reload(self):
        general_commands.handle_get(self.player, "Haven Map")

        imported = sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            shinobi_mud.WORLD_OVERLAYS,
        )

        self.assertEqual(imported["item_spawns"], 0)
        self.assertEqual(
            [item["name"] for item in room_items(self.player.cursor, 500, 500)],
            ["Travel Ration", "Water Flask"],
        )
        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Collector")],
            ["Haven Map"],
        )

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
            ["Haven Map", "Travel Ration", "Water Flask"],
        )
        self.assertEqual(inventory_items(self.player.cursor, "Collector"), [])

    def test_abbreviated_item_target_and_examination(self):
        self.player.x = 500
        self.player.y = 499

        general_commands.handle_examine(self.player, "kun")
        general_commands.handle_get(self.player, "kun")

        self.assertEqual(
            self.player.messages,
            [
                "Practice Kunai",
                "A dulled kunai balanced for training drills.",
                "Type: weapon",
                "Use: Wield it for training. Throwing attacks will arrive with ranged combat rules.",
                "You pick up Practice Kunai.",
            ],
        )

    def test_ordinal_item_target_selects_stable_duplicate(self):
        definition_id = self.connection.execute(
            "SELECT id FROM item_definitions WHERE item_key=?",
            ("practice-kunai",),
        ).fetchone()["id"]
        self.connection.execute(
            "INSERT INTO room_items (item_definition_id, x, y) VALUES (?, ?, ?)",
            (definition_id, 500, 499),
        )
        self.connection.commit()
        original_ids = [
            item["id"]
            for item in room_items(self.player.cursor, 500, 499)
            if item["name"] == "Practice Kunai"
        ]
        self.player.x = 500
        self.player.y = 499

        general_commands.handle_get(self.player, "2.kun")

        remaining_ids = [
            item["id"]
            for item in room_items(self.player.cursor, 500, 499)
            if item["name"] == "Practice Kunai"
        ]
        self.assertEqual(remaining_ids, [original_ids[0]])

    def test_wield_remove_and_equipment_persistence(self):
        self.player.x = 500
        self.player.y = 499
        general_commands.handle_get(self.player, "kun")
        general_commands.handle_wield(self.player, "kun")

        returning_player = TestProtocol(shinobi_mud.cursor)
        returning_player.username = "Collector"
        general_commands.handle_inventory(returning_player)
        general_commands.handle_remove(returning_player, "kun")

        self.assertEqual(
            returning_player.messages,
            [
                "Inventory",
                "  Carried: None",
                "  Equipped: hand: Practice Kunai",
                "You remove Practice Kunai.",
            ],
        )

    def test_look_at_item_uses_examination(self):
        self.player.x = 500
        self.player.y = 499

        general_commands.handle_look(self.player, raw_args="at kun")

        self.assertEqual(self.player.messages[0], "Practice Kunai")

    def test_eat_and_drink_restore_resources_and_remove_items(self):
        self.connection.execute(
            "UPDATE players SET nutrition=70, hydration=90 WHERE username=?",
            ("Collector",),
        )
        self.connection.commit()
        general_commands.handle_get(self.player, "ration")
        general_commands.handle_get(self.player, "flask")

        general_commands.handle_consume(self.player, "ration", "food", "nutrition", "eat")
        general_commands.handle_consume(self.player, "flask", "drink", "hydration", "drink")

        resources = self.connection.execute(
            "SELECT nutrition, hydration FROM players WHERE username=?",
            ("Collector",),
        ).fetchone()
        self.assertEqual(tuple(resources), (95, 100))
        self.assertEqual(inventory_items(self.player.cursor, "Collector"), [])
        self.assertEqual(
            self.player.messages[-2:],
            [
                "You eat Travel Ration and restore 25 nutrition.",
                "You drink Water Flask and restore 10 hydration.",
            ],
        )

    def test_consumption_rejects_missing_wrong_type_and_full_resource_without_destroying_items(self):
        general_commands.handle_get(self.player, "ration")
        general_commands.handle_get(self.player, "flask")

        general_commands.handle_consume(self.player, "missing", "food", "nutrition", "eat")
        general_commands.handle_consume(self.player, "flask", "food", "nutrition", "eat")
        general_commands.handle_consume(self.player, "ration", "food", "nutrition", "eat")

        self.assertEqual(
            self.player.messages[-3:],
            [
                "You are not carrying that item.",
                "You cannot eat Water Flask.",
                "Your nutrition is already full.",
            ],
        )
        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Collector")],
            ["Travel Ration", "Water Flask"],
        )

    def test_ordinal_consumption_removes_only_selected_item(self):
        definition_id = self.connection.execute(
            "SELECT id FROM item_definitions WHERE item_key=?",
            ("travel-ration",),
        ).fetchone()["id"]
        player_id = self.connection.execute(
            "SELECT id FROM players WHERE username=?",
            ("Collector",),
        ).fetchone()["id"]
        self.connection.executemany(
            "INSERT INTO character_inventory (item_definition_id, player_id) VALUES (?, ?)",
            [(definition_id, player_id), (definition_id, player_id)],
        )
        self.connection.execute(
            "UPDATE players SET nutrition=50 WHERE username=?",
            ("Collector",),
        )
        self.connection.commit()

        general_commands.handle_consume(self.player, "2.ration", "food", "nutrition", "eat")

        self.assertEqual(
            [item["name"] for item in inventory_items(self.player.cursor, "Collector")],
            ["Travel Ration"],
        )

    def test_consumed_authored_item_does_not_respawn_after_content_reload(self):
        self.connection.execute(
            "UPDATE players SET nutrition=50 WHERE username=?",
            ("Collector",),
        )
        self.connection.commit()
        general_commands.handle_get(self.player, "ration")
        general_commands.handle_consume(self.player, "ration", "food", "nutrition", "eat")

        imported = sync_authored_content(
            self.connection,
            str(PROJECT_ROOT / "zones"),
            shinobi_mud.WORLD_OVERLAYS,
        )

        self.assertEqual(imported["item_spawns"], 0)
        self.assertNotIn(
            "Travel Ration",
            [item["name"] for item in room_items(self.player.cursor, 500, 500)],
        )

    def test_consumable_migration_preserves_existing_item_definitions(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE item_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                description TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO item_definitions (item_key, name, description) VALUES (?, ?, ?)",
            ("legacy-item", "Legacy Item", "Still present."),
        )

        migration_008_consumable_items(connection.cursor())

        item = connection.execute(
            "SELECT name, nutrition_restore, hydration_restore FROM item_definitions"
        ).fetchone()
        self.assertEqual(tuple(item), ("Legacy Item", 0, 0))
        connection.close()


if __name__ == "__main__":
    unittest.main()
