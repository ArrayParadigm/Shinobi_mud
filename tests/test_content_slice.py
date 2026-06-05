import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import admin_commands
import general_commands
import veilborn_mud
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
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.world_map = [list("...."), list("...."), list("....")]
        self.original_general_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        self.player = self.create_player("Explorer", 1, 1)

    def tearDown(self):
        general_commands.UTILITIES["WORLD_MAP"] = self.original_general_map
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def create_player(self, username, x, y):
        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            (username, "hash", x, y),
        )
        self.connection.commit()
        player = TestProtocol(veilborn_mud.cursor)
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
                utils.preload_zones_with_anchors(veilborn_mud.WORLD_OVERLAYS, "zones")
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
        veilborn_mud.WORLD_OVERLAYS[(2, 1)] = {
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
            veilborn_mud.players_in_rooms,
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
        veilborn_mud.WORLD_OVERLAYS[(2, 1)] = {
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
        veilborn_mud.WORLD_OVERLAYS[(2, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {"description": "A compact town square.", "exits": {}},
        }
        self.connection.execute(
            "UPDATE players SET password=? WHERE username=?",
            (veilborn_mud.hash_password("password"), "Explorer"),
        )
        self.connection.commit()
        general_commands.handle_movement(self.player, "east")
        veilborn_mud.players_in_rooms.clear()
        returning_player = TestProtocol(veilborn_mud.cursor)

        returning_player.handle_username("Explorer")
        returning_player.handle_password("password")

        self.assertEqual((returning_player.x, returning_player.y), (2, 1))
        self.assertEqual(
            veilborn_mud.WORLD_OVERLAYS[(returning_player.x, returning_player.y)]["vnum"],
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
                self.assertEqual(veilborn_mud.WORLD_OVERLAYS[(10, 20)]["vnum"], 7000)
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
                veilborn_mud.WORLD_OVERLAYS[(99, 99)] = {"vnum": 9999}

                admin_commands.placezone(self.player, "sample", "10", "20")

                zone_data = json.loads(zone_path.read_text(encoding="utf-8"))
                self.assertNotIn("anchor", zone_data)
                self.assertEqual(veilborn_mud.WORLD_OVERLAYS, {})
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
                self.assertEqual(veilborn_mud.WORLD_OVERLAYS, {})
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
            self.assertEqual(veilborn_mud.WORLD_OVERLAYS[(1, 0)]["vnum"], 7001)

            self.player.x, self.player.y = 1, 0
            admin_commands.roomdesc(self.player, "A reinforced sparring alcove.")
            veilborn_mud.WORLD_OVERLAYS.clear()
            utils.preload_zones_with_anchors(veilborn_mud.WORLD_OVERLAYS, "zones")

            self.assertEqual(
                veilborn_mud.WORLD_OVERLAYS[(1, 0)]["room"]["description"],
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
            sync_authored_content(self.connection, "zones", veilborn_mud.WORLD_OVERLAYS)

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
                        "max_health": 10,
                        "max_stamina": 10,
                        "max_wisp": 10,
                        "strength": 10,
                        "dexterity": 10,
                        "agility": 10,
                        "intelligence": 10,
                        "wisdom": 10,
                        "movement_policy": "static",
                        "leash_radius": 0,
                        "aggression_policy": "passive",
                        "loot_table": [],
                        "combat_techniques": [],
                        "expressions": [],
                        "room_emote": "",
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
                self.assertEqual(veilborn_mud.WORLD_OVERLAYS[(10, 20)]["vnum"], 7000)
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
            utils.render_room(self.player, veilborn_mud.WORLD_OVERLAYS)

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

    def test_redit_link_unlink_records_reciprocal_audit(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7001},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"name": "Square", "description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0},
                "7001": {"name": "North", "description": "North.", "exits": {}, "x_offset": 0, "y_offset": -1},
            },
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.redit(self.player, "link", "north 7001")
            linked = json.loads(zone_path.read_text(encoding="utf-8"))
            admin_commands.redit(self.player, "unlink", "north")
            unlinked = json.loads(zone_path.read_text(encoding="utf-8"))

        audit = self.connection.execute(
            """
            SELECT action, target, details
            FROM builder_audit
            ORDER BY id
            """
        ).fetchall()

        self.assertEqual(linked["rooms"]["7000"]["exits"], {"north": 7001})
        self.assertEqual(linked["rooms"]["7001"]["exits"], {"south": 7000})
        self.assertEqual(unlinked["rooms"]["7000"]["exits"], {})
        self.assertEqual(unlinked["rooms"]["7001"]["exits"], {})
        self.assertEqual(
            [tuple(row) for row in audit],
            [("redit link", "7000", "north 7001"), ("redit unlink", "7000", "north")],
        )

    def test_publish_guarded_delete_and_undo_restore_zone_json(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7001},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"name": "Square", "description": "Square.", "exits": {"north": 7001}, "x_offset": 0, "y_offset": 0},
                "7001": {"name": "North", "description": "North.", "exits": {"south": 7000}, "x_offset": 0, "y_offset": -1},
            },
            "item_templates": [{"key": "ration", "name": "Field Ration", "description": "A meal.", "keywords": ["meal"], "item_type": "food"}],
            "item_spawns": [{"key": "ration-7001", "item": "ration", "vnum": 7001}],
            "npc_templates": [],
            "npc_spawns": [],
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.rdelete(self.player, "7001")
            admin_commands.redit(self.player, "unlink", "north")
            admin_commands.rdelete(self.player, "7001")
            admin_commands.despawnitem(self.player, "ration-7001")
            admin_commands.rdelete(self.player, "7001")
            admin_commands.zpublish(self.player, "sample")
            published = json.loads(zone_path.read_text(encoding="utf-8"))
            admin_commands.zdelete(self.player, "sample")
            self.assertFalse(zone_path.exists())
            admin_commands.bundo(self.player)
            restored = json.loads(zone_path.read_text(encoding="utf-8"))

        transcript = "\n".join(self.player.messages)
        audit = self.connection.execute(
            "SELECT action, target, details FROM builder_audit ORDER BY id"
        ).fetchall()

        self.assertIn("Unable to delete room: room [7001] still has exits", transcript)
        self.assertIn("item spawn ration-7001 still references [7001]", transcript)
        self.assertIn("Deleted room [7001].", transcript)
        self.assertTrue(published["published"])
        self.assertIn("Deleted zone sample.json.", transcript)
        self.assertEqual(restored["name"], "Sample")
        self.assertIn(("zpublish", "sample.json", "Published zone after validation."), [tuple(row) for row in audit])
        self.assertIn(("zdelete", "sample.json", "Deleted zone Sample"), [tuple(row) for row in audit])

    def test_zpublish_refuses_invalid_draft(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7001},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"name": "Square", "description": "Square.", "exits": {"north": 7999}, "x_offset": 0, "y_offset": 0},
            },
        }
        with self.temporary_zone(zone_data) as zone_path:
            admin_commands.zpublish(self.player, "sample")
            persisted = json.loads(zone_path.read_text(encoding="utf-8"))

        self.assertNotIn("published", persisted)
        self.assertIn(
            "Unable to publish zone: Room [7000] exit north points to missing VNUM 7999.",
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
            sync_authored_content(self.connection, "zones", veilborn_mud.WORLD_OVERLAYS)
            admin_commands.createnpc(self.player, "guard", "Village Guard")
            admin_commands.medit(self.player, "guard", "behavior", "hostile")
            admin_commands.medit(self.player, "guard", "health", "15")
            admin_commands.medit(self.player, "guard", "damage", "4")
            admin_commands.medit(self.player, "guard", "movement", "leashed")
            admin_commands.medit(self.player, "guard", "leash", "2")
            admin_commands.medit(self.player, "guard", "aggression", "aggressive")
            admin_commands.medit(self.player, "guard", "emote", "The guard watches the street.")
            admin_commands.mstat(self.player, "guard")

            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            template = persisted["npc_templates"][0]
            saved = self.connection.execute(
                "SELECT behavior, max_health, attack_damage, movement_policy, leash_radius, aggression_policy, room_emote FROM npc_templates WHERE npc_key='guard'"
            ).fetchone()
            self.assertEqual(template["behavior"], "hostile")
            self.assertEqual(template["max_health"], 15)
            self.assertEqual(tuple(saved), ("hostile", 15, 4, "leashed", 2, "aggressive", "The guard watches the street."))
            self.assertIn("NPC guard: Village Guard", self.player.messages)
            self.assertIn("  AI: movement=leashed leash=2 aggression=aggressive", self.player.messages)
            self.assertIn("  Resources: health=15 stamina=10 wisp=10", self.player.messages)
            self.assertIn("  Stats: str=10 dex=10 agi=10 int=10 wis=10", self.player.messages)
            self.assertIn("  Combat: damage_bonus=4 accuracy_bonus=5 evasion_bonus=5 respawn=60s", self.player.messages)

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
            sync_authored_content(self.connection, "zones", veilborn_mud.WORLD_OVERLAYS)
            admin_commands.iedit(self.player, "create", "", "field-ration Field Ration")
            admin_commands.iedit(self.player, "field-ration", "type", "food")
            admin_commands.iedit(self.player, "field-ration", "nutrition", "30")
            admin_commands.iedit(self.player, "field-ration", "value", "3")
            admin_commands.iedit(self.player, "field-ration", "weight", "1")
            admin_commands.iedit(self.player, "field-ration", "stack", "5")
            admin_commands.iedit(self.player, "field-ration", "flags", "takeable consumable")
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
            self.assertIn("  Economy: value=3 weight=1 stack=5 capacity=0", self.player.messages)
            self.assertIn("  Flags: takeable, consumable", self.player.messages)

    def test_builder_inventory_search_and_contentcheck_cover_zone_json(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7001},
            "anchor": {"x": 1, "y": 1},
            "rooms": {
                "7000": {"name": "Square", "description": "Square.", "exits": {"north": 7001}, "x_offset": 0, "y_offset": 0},
                "7001": {"name": "North", "description": "North.", "exits": {"south": 7000}, "x_offset": 0, "y_offset": -1},
            },
            "npc_templates": [{"key": "guard", "name": "Village Guard", "description": "A guard.", "dialogue": "Stay sharp.", "behavior": "static"}],
            "item_templates": [{"key": "ration", "name": "Field Ration", "description": "A meal.", "keywords": ["meal"], "item_type": "food"}],
            "npc_spawns": [{"key": "guard-7000", "npc": "guard", "vnum": 7000}],
            "item_spawns": [{"key": "ration-7000", "item": "ration", "vnum": 7000}],
        }
        with self.temporary_zone(zone_data):
            admin_commands.zstat(self.player, "sample")
            admin_commands.rlist(self.player, "sample")
            admin_commands.mlist(self.player, "sample")
            admin_commands.ilist(self.player, "sample")
            admin_commands.bfind(self.player, "guard")
            admin_commands.contentcheck(self.player, "sample")

        transcript = "\n".join(self.player.messages)
        self.assertIn("Zone Sample (sample.json)", transcript)
        self.assertIn("  [7000] Square (0, 0)", transcript)
        self.assertIn("  guard: Village Guard (static)", transcript)
        self.assertIn("  ration: Field Ration (food)", transcript)
        self.assertIn("  npc Sample guard: Village Guard", transcript)
        self.assertIn("Content Check\n  OK", transcript)

    def test_contentcheck_rejects_invalid_rich_template_fields(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7000},
            "anchor": {"x": 1, "y": 1},
            "rooms": {"7000": {"name": "Square", "description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0}},
            "npc_templates": [{
                "key": "guard",
                "name": "Village Guard",
                "description": "A guard.",
                "dialogue": "Stay sharp.",
                "behavior": "flying",
                "movement_policy": "teleport",
                "aggression_policy": "mean",
                "loot_table": ["missing-item"],
            }],
            "item_templates": [{
                "key": "ration",
                "name": "Field Ration",
                "description": "A meal.",
                "keywords": ["meal"],
                "item_type": "artifact",
                "equipment_slot": "tail",
                "flags": ["cursed"],
                "stack_limit": 0,
            }],
        }
        with self.temporary_zone(zone_data):
            admin_commands.contentcheck(self.player, "sample")

        transcript = "\n".join(self.player.messages)
        self.assertIn("Item template ration has unsupported type artifact.", transcript)
        self.assertIn("Item template ration has unsupported slot tail.", transcript)
        self.assertIn("Item template ration has unsupported flags cursed.", transcript)
        self.assertIn("Item template ration has stack_limit below 1.", transcript)
        self.assertIn("NPC template guard has unsupported behavior flying.", transcript)
        self.assertIn("NPC template guard has unsupported movement teleport.", transcript)
        self.assertIn("NPC template guard has unsupported aggression mean.", transcript)
        self.assertIn("NPC template guard loot references missing item missing-item.", transcript)

    def test_builder_clone_despawn_and_bundo_round_trip_zone_json(self):
        zone_data = {
            "name": "Sample",
            "content_key": "sample",
            "range": {"start": 7000, "end": 7002},
            "anchor": {"x": 1, "y": 1},
            "rooms": {"7000": {"name": "Square", "description": "Square.", "exits": {}, "x_offset": 0, "y_offset": 0}},
            "npc_templates": [{"key": "guard", "name": "Village Guard", "description": "A guard.", "dialogue": "Stay sharp.", "behavior": "static"}],
            "item_templates": [{"key": "ration", "name": "Field Ration", "description": "A meal.", "keywords": ["meal"], "item_type": "food"}],
            "npc_spawns": [{"key": "guard-7000", "npc": "guard", "vnum": 7000}],
            "item_spawns": [{"key": "ration-7000", "item": "ration", "vnum": 7000}],
        }
        with self.temporary_zone(zone_data) as zone_path:
            sync_authored_content(self.connection, "zones", veilborn_mud.WORLD_OVERLAYS)

            admin_commands.cloneitem(self.player, "ration", "ration-copy")
            admin_commands.clonenpc(self.player, "guard", "guard-copy")
            admin_commands.cloneroom(self.player, "7000", "7001")
            admin_commands.despawnitem(self.player, "ration-7000")
            persisted = json.loads(zone_path.read_text(encoding="utf-8"))
            self.assertNotIn("ration-7000", [spawn["key"] for spawn in persisted["item_spawns"]])

            admin_commands.bundo(self.player)
            restored = json.loads(zone_path.read_text(encoding="utf-8"))

        self.assertIn("ration-copy", [item["key"] for item in restored["item_templates"]])
        self.assertIn("guard-copy", [npc["key"] for npc in restored["npc_templates"]])
        self.assertIn("7001", restored["rooms"])
        self.assertIn("ration-7000", [spawn["key"] for spawn in restored["item_spawns"]])
        self.assertIn("Undid builder action: zone edit.", self.player.messages)

    def test_hedit_updates_help_category_and_publish_state(self):
        original_help = veilborn_mud.ACTIVE_CONFIG.get("help_file")
        original_categories = veilborn_mud.ACTIVE_CONFIG.get("command_categories_file")
        original_admin_help = admin_commands.ACTIVE_CONFIG.get("help_file")
        original_admin_categories = admin_commands.ACTIVE_CONFIG.get("command_categories_file")
        with tempfile.TemporaryDirectory() as temporary_directory:
            help_path = Path(temporary_directory) / "commands.json"
            category_path = Path(temporary_directory) / "command_categories.json"
            help_path.write_text(
                json.dumps({"look": {"summary": "Old look.", "details": [], "published": False}}),
                encoding="utf-8",
            )
            category_path.write_text(json.dumps({"Other": ["look"]}), encoding="utf-8")
            veilborn_mud.ACTIVE_CONFIG["help_file"] = str(help_path)
            veilborn_mud.ACTIVE_CONFIG["command_categories_file"] = str(category_path)
            admin_commands.ACTIVE_CONFIG["help_file"] = str(help_path)
            admin_commands.ACTIVE_CONFIG["command_categories_file"] = str(category_path)

            admin_commands.hedit(self.player, "look", "summary", "Updated look.")
            admin_commands.hedit(self.player, "look", "detail", "Use this to read a room.")
            admin_commands.hedit(self.player, "look", "category", "Exploration")
            admin_commands.hedit(self.player, "look", "publish")
            catalog = json.loads(help_path.read_text(encoding="utf-8"))
            categories = json.loads(category_path.read_text(encoding="utf-8"))

        if original_help is None:
            veilborn_mud.ACTIVE_CONFIG.pop("help_file", None)
        else:
            veilborn_mud.ACTIVE_CONFIG["help_file"] = original_help
        if original_categories is None:
            veilborn_mud.ACTIVE_CONFIG.pop("command_categories_file", None)
        else:
            veilborn_mud.ACTIVE_CONFIG["command_categories_file"] = original_categories
        if original_admin_help is None:
            admin_commands.ACTIVE_CONFIG.pop("help_file", None)
        else:
            admin_commands.ACTIVE_CONFIG["help_file"] = original_admin_help
        if original_admin_categories is None:
            admin_commands.ACTIVE_CONFIG.pop("command_categories_file", None)
        else:
            admin_commands.ACTIVE_CONFIG["command_categories_file"] = original_admin_categories

        self.assertEqual(catalog["look"]["summary"], "Updated look.")
        self.assertEqual(catalog["look"]["details"], ["Use this to read a room."])
        self.assertTrue(catalog["look"]["published"])
        self.assertEqual(categories["Exploration"], ["look"])

    def test_room_flags_have_visible_player_consequences(self):
        veilborn_mud.WORLD_OVERLAYS[(1, 1)] = {
            "zone_name": "Flag Lab",
            "vnum": 7000,
            "room": {"name": "Dark Safe Room", "description": "Dark.", "flags": ["darkness", "safe"], "exits": {"east": 7001}},
        }
        veilborn_mud.WORLD_OVERLAYS[(2, 1)] = {
            "zone_name": "Flag Lab",
            "vnum": 7001,
            "room": {"name": "Vacuum Room", "description": "Thin air.", "flags": ["vacuum", "recovery-friendly"], "exits": {"west": 7000}},
        }

        general_commands.handle_survey(self.player)
        general_commands.handle_attack(self.player, "anything")
        before_move_messages = list(self.player.messages)
        general_commands.handle_movement(self.player, "east")
        movement_messages = list(self.player.messages)
        fatigue = self.connection.execute(
            "SELECT fatigue FROM players WHERE username='Explorer'"
        ).fetchone()["fatigue"]
        self.connection.execute(
            "UPDATE players SET stamina=2, wisp=1, fatigue=30 WHERE username='Explorer'"
        )
        self.connection.commit()
        self.player.messages.clear()
        general_commands.handle_rest(self.player)
        saved = self.connection.execute(
            "SELECT stamina, wisp, fatigue FROM players WHERE username='Explorer'"
        ).fetchone()

        self.assertIn("It is too dark to survey the area.", before_move_messages)
        self.assertIn("Combat is not allowed here.", before_move_messages)
        self.assertIn("Vacuum strains your body.", "\n".join(movement_messages))
        self.assertGreater(fatigue, 0)
        self.assertIn("This room supports recovery.", self.player.messages)
        self.assertGreater(saved["stamina"], 2)
        self.assertGreater(saved["wisp"], 1)
        self.assertLess(saved["fatigue"], 30)


if __name__ == "__main__":
    unittest.main()
