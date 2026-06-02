import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import admin_commands
import general_commands
import shinobi_mud
import social_commands
import utils
from content import sync_authored_content
from migrations import apply_migrations
from npcs import npcs_at
from tests.test_accounts import TestProtocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ContentSliceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.world_map = [list("...."), list("...."), list("....")]
        self.original_general_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        self.player = self.create_player("Explorer", 1, 1)

    def tearDown(self):
        general_commands.UTILITIES["WORLD_MAP"] = self.original_general_map
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def create_player(self, username, x, y):
        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            (username, "hash", x, y),
        )
        self.connection.commit()
        player = TestProtocol(shinobi_mud.cursor)
        player.username = username
        player.x = x
        player.y = y
        player.state = "COMMAND"
        player.track_player()
        player.messages.clear()
        return player

    @contextmanager
    def temporary_zone(self, zone_data):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                Path("zones").mkdir()
                zone_path = Path("zones/sample.json")
                zone_path.write_text(json.dumps(zone_data), encoding="utf-8")
                utils.preload_zones_with_anchors(shinobi_mud.WORLD_OVERLAYS, "zones")
                yield zone_path
            finally:
                os.chdir(original_directory)

    def test_eves_haven_loads_distinct_rooms_from_persisted_anchor(self):
        overlays = utils.preload_zones_with_anchors(
            {},
            str(PROJECT_ROOT / "zones"),
        )

        self.assertGreaterEqual(len(overlays), 30)
        self.assertEqual(overlays[(500, 500)]["vnum"], 3000)
        self.assertEqual(overlays[(500, 499)]["vnum"], 3001)
        self.assertEqual(overlays[(1, 1)]["vnum"], 1000)
        self.assertEqual(
            utils.find_overlay_by_vnum(overlays, 3029)[1]["zone_name"],
            "Eve's Haven",
        )

    def test_entry_exit_chat_and_overlay_description_remain_coordinate_first(self):
        shinobi_mud.WORLD_OVERLAYS[(2, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {"description": "A compact town square.", "exits": {"west": 2999}},
        }
        resident = self.create_player("Resident", 2, 1)

        general_commands.handle_movement(self.player, "east")
        social_commands.handle_say(
            self.player,
            "hello",
            ["hello"],
            shinobi_mud.players_in_rooms,
        )
        general_commands.handle_movement(self.player, "west")

        self.assertIn("Test Town [3000]\nA compact town square.\n\nExits: west", self.player.messages)
        self.assertIn('Explorer says, "hello"', resident.messages)
        self.assertIn("Open Land\nYou see open land around you.", self.player.messages)
        self.assertEqual((self.player.x, self.player.y), (1, 1))
        saved = self.connection.execute(
            "SELECT x, y FROM players WHERE username=?",
            ("Explorer",),
        ).fetchone()
        self.assertEqual(tuple(saved), (1, 1))

    def test_admin_goto_and_zoneinfo_use_overlay_coordinates(self):
        shinobi_mud.WORLD_OVERLAYS[(2, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {"description": "A compact town square.", "exits": {}},
        }

        admin_commands.goto(self.player, "3000")
        admin_commands.zoneinfo(self.player)

        self.assertEqual((self.player.x, self.player.y), (2, 1))
        self.assertIn("Teleported to Test Town [3000] at (2, 1).", self.player.messages)
        self.assertIn("Test Town [3000] at (2, 1)", self.player.messages)

    def test_admin_goto_grid_and_player_use_canonical_coordinates(self):
        target = self.create_player("Target", 3, 2)

        admin_commands.goto(self.player, "grid", "2", "1")
        admin_commands.goto(self.player, "player", "Target")

        self.assertEqual((self.player.x, self.player.y), (3, 2))
        self.assertIn("Teleported to grid location (2, 1).", self.player.messages)
        self.assertIn("Teleported to Target at (3, 2).", self.player.messages)

        target.untrack_player()

    def test_copyover_reports_disabled_status(self):
        admin_commands.copyover(self.player)

        self.assertEqual(
            self.player.messages,
            [
                "Copyover is disabled for now. Restart the server normally; players can reconnect safely."
            ],
        )

    def test_reconnect_restores_coordinate_inside_overlay(self):
        shinobi_mud.WORLD_OVERLAYS[(2, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {"description": "A compact town square.", "exits": {}},
        }
        self.connection.execute(
            "UPDATE players SET password=? WHERE username=?",
            (shinobi_mud.hash_password("password"), "Explorer"),
        )
        self.connection.commit()
        general_commands.handle_movement(self.player, "east")
        shinobi_mud.players_in_rooms.clear()
        returning_player = TestProtocol(shinobi_mud.cursor)

        returning_player.handle_username("Explorer")
        returning_player.handle_password("password")

        self.assertEqual((returning_player.x, returning_player.y), (2, 1))
        self.assertEqual(
            shinobi_mud.WORLD_OVERLAYS[(returning_player.x, returning_player.y)]["vnum"],
            3000,
        )

    def test_placezone_persists_anchor_and_reloads_overlays(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                Path("zones").mkdir()
                zone_path = Path("zones/sample.json")
                zone_path.write_text(
                    json.dumps(
                        {
                            "name": "Sample",
                            "range": {"start": 7000, "end": 7000},
                            "rooms": {
                                "7000": {
                                    "description": "Sample square.",
                                    "exits": {},
                                    "x_offset": 0,
                                    "y_offset": 0,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

                admin_commands.placezone(self.player, "sample", "10", "20")

                zone_data = json.loads(zone_path.read_text(encoding="utf-8"))
                self.assertEqual(zone_data["anchor"], {"x": 10, "y": 20})
                self.assertEqual(shinobi_mud.WORLD_OVERLAYS[(10, 20)]["vnum"], 7000)
            finally:
                os.chdir(original_directory)

    def test_failed_placezone_rolls_back_anchor_and_live_overlays(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                Path("zones").mkdir()
                zone_path = Path("zones/sample.json")
                zone_path.write_text(
                    json.dumps(
                        {
                            "name": "Sample",
                            "range": {"start": 7000, "end": 7001},
                            "rooms": {
                                "7000": {"description": "One.", "exits": {}},
                                "7001": {"description": "Two.", "exits": {}},
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                shinobi_mud.WORLD_OVERLAYS[(99, 99)] = {"vnum": 9999}

                admin_commands.placezone(self.player, "sample", "10", "20")

                zone_data = json.loads(zone_path.read_text(encoding="utf-8"))
                self.assertNotIn("anchor", zone_data)
                self.assertEqual(shinobi_mud.WORLD_OVERLAYS, {})
                self.assertIn("Unable to place zone", self.player.messages[-1])
            finally:
                os.chdir(original_directory)

    def test_out_of_bounds_placezone_rolls_back_anchor(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                Path("zones").mkdir()
                zone_path = Path("zones/sample.json")
                zone_path.write_text(
                    json.dumps(
                        {
                            "name": "Sample",
                            "range": {"start": 7000, "end": 7000},
                            "rooms": {
                                "7000": {
                                    "description": "Sample square.",
                                    "exits": {},
                                    "x_offset": 0,
                                    "y_offset": 0,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )

                admin_commands.placezone(self.player, "sample", "-1", "20")

                zone_data = json.loads(zone_path.read_text(encoding="utf-8"))
                self.assertNotIn("anchor", zone_data)
                self.assertEqual(shinobi_mud.WORLD_OVERLAYS, {})
                self.assertIn("outside the world map", self.player.messages[-1])
            finally:
                os.chdir(original_directory)

    def test_dig_and_roomdesc_persist_coordinate_overlay_edits(self):
        zone_data = {
            "name": "Sample",
            "range": {"start": 7000, "end": 7002},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {
                    "description": "Sample square.",
                    "exits": {},
                    "x_offset": 0,
                    "y_offset": 0,
                }
            },
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.dig(self.player, "north", "A sparring alcove.")

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["rooms"]["7000"]["exits"], {"north": 7001})
            self.assertEqual(
                persisted["rooms"]["7001"],
                {
                    "name": "A sparring alcove.",
                    "description": "An unfinished authored room.",
                    "flags": [],
                    "exits": {"south": 7000},
                    "x_offset": 0,
                    "y_offset": -1,
                },
            )
            self.assertEqual(shinobi_mud.WORLD_OVERLAYS[(1, 0)]["vnum"], 7001)

            self.player.x, self.player.y = 1, 0
            admin_commands.roomdesc(self.player, "A reinforced sparring alcove.")
            shinobi_mud.WORLD_OVERLAYS.clear()
            utils.preload_zones_with_anchors(shinobi_mud.WORLD_OVERLAYS, "zones")

            self.assertEqual(
                shinobi_mud.WORLD_OVERLAYS[(1, 0)]["room"]["description"],
                "A reinforced sparring alcove.",
            )

    def test_dig_rejects_occupied_overlay_coordinate(self):
        zone_data = {
            "name": "Sample",
            "range": {"start": 7000, "end": 7002},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0},
                "7001": {"description": "Occupied.", "exits": {}, "x_offset": 0, "y_offset": -1},
            },
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.dig(self.player, "north", "Replacement.")

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            self.assertNotIn("7002", persisted["rooms"])
            self.assertIn("already exists", self.player.messages[-1])

    def test_spawnnpc_persists_authored_spawn_without_reload_duplication(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7000},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {
                    "description": "Sample square.",
                    "exits": {},
                    "x_offset": 0,
                    "y_offset": 0,
                }
            },
            "npc_templates": [],
            "npc_spawns": [],
        }
        with self.temporary_zone(zone_data) as zone_path:
            sync_authored_content(self.connection, "zones", shinobi_mud.WORLD_OVERLAYS)

            admin_commands.createnpc(self.player, "practice-dummy", "Practice Dummy")
            admin_commands.spawnnpc(self.player, "practice-dummy")
            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            admin_commands.reloadcontent(self.player)

            self.assertEqual(
                persisted["npc_templates"],
                [
                    {
                        "key": "practice-dummy",
                        "name": "Practice Dummy",
                        "description": "Practice Dummy waits here.",
                        "dialogue": "Practice Dummy has nothing to say yet.",
                        "behavior": "static",
                    }
                ],
            )
            self.assertEqual(
                persisted["npc_spawns"],
                [{"key": "builder-practice-dummy-7000", "npc": "practice-dummy", "vnum": 7000}],
            )
            self.assertEqual(
                [npc["name"] for npc in npcs_at(self.player.cursor, 1, 1)],
                ["Practice Dummy"],
            )
            self.assertIn("Created 0 item spawns and 0 NPC spawns.", self.player.messages[-1])

    def test_buildzone_creates_anchored_starting_room_and_lists_zone(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                Path("zones").mkdir()

                admin_commands.buildzone(
                    self.player,
                    "training-yard",
                    "7000",
                    "7099",
                    "10",
                    "20",
                    "Training Yard",
                )
                admin_commands.zonelist(self.player)

                persisted = json.loads(Path("zones/training-yard.json").read_text(encoding="utf-8"))
                self.assertEqual(persisted["anchor"], {"x": 10, "y": 20})
                self.assertEqual(persisted["rooms"]["7000"]["name"], "Training Yard")
                self.assertEqual((self.player.x, self.player.y), (10, 20))
                self.assertEqual(shinobi_mud.WORLD_OVERLAYS[(10, 20)]["vnum"], 7000)
                self.assertIn(
                    "  training-yard.json: Training Yard [7000-7099] anchor=(10, 20) rooms=1",
                    self.player.messages,
                )
            finally:
                os.chdir(original_directory)

    def test_redit_rstat_and_render_room_expose_titles_flags_and_exits(self):
        zone_data = {
            "name": "Sample",
            "range": {"start": 7000, "end": 7001},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0},
                "7001": {"description": "North.", "exits": {}, "x_offset": 0, "y_offset": -1},
            },
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.redit(self.player, "title", "Village Square")
            admin_commands.redit(self.player, "desc", "A welcoming village square.")
            admin_commands.redit(self.player, "flag", "outdoor on")
            admin_commands.redit(self.player, "exit", "north 7001")
            admin_commands.rstat(self.player)
            utils.render_room(self.player, shinobi_mud.WORLD_OVERLAYS)

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["rooms"]["7000"]["name"], "Village Square")
            self.assertEqual(persisted["rooms"]["7000"]["flags"], ["outdoor"])
            self.assertEqual(persisted["rooms"]["7000"]["exits"], {"north": 7001})
            self.assertIn("Room [7000] Village Square", self.player.messages)
            self.assertIn("  Flags: outdoor", self.player.messages)
            self.assertIn(
                "Village Square [7000]\nA welcoming village square.\n\nExits: north",
                self.player.messages,
            )

    def test_medit_and_mstat_sync_authored_npc_fields(self):
        zone_data = {
            "name": "Sample",
            "range": {"start": 7000, "end": 7000},
            "anchor": {"x": 1, "y": 1},
            "rooms": {"7000": {"description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0}},
            "npc_templates": [],
        }
        with self.temporary_zone(zone_data) as zone_path:
            sync_authored_content(self.connection, "zones", shinobi_mud.WORLD_OVERLAYS)
            admin_commands.createnpc(self.player, "guard", "Village Guard")
            admin_commands.medit(self.player, "guard", "behavior", "hostile")
            admin_commands.medit(self.player, "guard", "health", "15")
            admin_commands.medit(self.player, "guard", "damage", "4")
            admin_commands.mstat(self.player, "guard")

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            template = persisted["npc_templates"][0]
            saved = self.connection.execute(
                "SELECT behavior, max_health, attack_damage FROM npc_templates WHERE npc_key='guard'"
            ).fetchone()
            self.assertEqual(template["behavior"], "hostile")
            self.assertEqual(template["max_health"], 15)
            self.assertEqual(tuple(saved), ("hostile", 15, 4))
            self.assertIn("NPC guard: Village Guard", self.player.messages)
            self.assertIn("  Combat: health=15 damage=4 accuracy=5 evasion=5 respawn=60s", self.player.messages)

    def test_iedit_spawnitem_and_istat_keep_consumed_seed_finite(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7000},
            "anchor": {"x": 1, "y": 1},
            "rooms": {"7000": {"description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0}},
            "item_templates": [],
            "item_spawns": [],
        }
        with self.temporary_zone(zone_data) as zone_path:
            sync_authored_content(self.connection, "zones", shinobi_mud.WORLD_OVERLAYS)
            admin_commands.iedit(self.player, "create", "", "field-ration Field Ration")
            admin_commands.iedit(self.player, "field-ration", "type", "food")
            admin_commands.iedit(self.player, "field-ration", "nutrition", "30")
            admin_commands.spawnitem(self.player, "field-ration")
            admin_commands.istat(self.player, "field-ration")

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["item_spawns"],
                [{"key": "builder-field-ration-7000", "item": "field-ration", "vnum": 7000}],
            )
            self.assertEqual(
                self.connection.execute("SELECT COUNT(*) FROM room_items").fetchone()[0],
                1,
            )
            self.connection.execute("DELETE FROM room_items")
            self.connection.commit()
            admin_commands.reloadcontent(self.player)
            self.assertEqual(
                self.connection.execute("SELECT COUNT(*) FROM room_items").fetchone()[0],
                0,
            )
            self.assertIn("Item field-ration: Field Ration", self.player.messages)
            self.assertIn("  Type: food slot=None damage=0 throw=0 nutrition=30 hydration=0", self.player.messages)


if __name__ == "__main__":
    unittest.main()
