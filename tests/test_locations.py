import sqlite3
import unittest

import general_commands
import veilborn_mud
import utils
from auth import hash_password
from locations import LocationPersistenceError, get_location, move_player, nearby_players, players_at, track_player
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.world_map = [list("..."), list("..."), list("...")]

        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            ("Walker", "hash", 1, 1),
        )
        self.connection.commit()
        self.player = TestProtocol(veilborn_mud.cursor)
        self.player.username = "Walker"
        self.player.x = 1
        self.player.y = 1
        track_player(self.player, veilborn_mud.players_in_rooms)

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_move_updates_tracking_bucket_and_database(self):
        moved = move_player(
            self.player,
            "east",
            self.world_map,
            veilborn_mud.players_in_rooms,
        )

        self.assertTrue(moved)
        self.assertEqual((self.player.x, self.player.y), (2, 1))
        self.assertNotIn((1, 1), veilborn_mud.players_in_rooms)
        self.assertEqual(veilborn_mud.players_in_rooms[(2, 1)], [self.player])
        saved = self.connection.execute(
            "SELECT x, y, fatigue FROM players WHERE username=?",
            ("Walker",),
        ).fetchone()
        self.assertEqual(tuple(saved), (2, 1, 1))

    def test_move_accepts_subcardinal_directions(self):
        moved = move_player(
            self.player,
            "northeast",
            self.world_map,
            veilborn_mud.players_in_rooms,
        )

        self.assertTrue(moved)
        self.assertEqual((self.player.x, self.player.y), (2, 0))

    def test_login_restores_coordinates_saved_by_movement(self):
        self.connection.execute(
            "UPDATE players SET password=? WHERE username=?",
            (hash_password("password"), "Walker"),
        )
        self.connection.commit()
        move_player(self.player, "east", self.world_map, veilborn_mud.players_in_rooms)
        veilborn_mud.players_in_rooms.clear()
        returning_player = TestProtocol(veilborn_mud.cursor)

        returning_player.handle_username("Walker")
        returning_player.handle_password("password")

        self.assertEqual((returning_player.x, returning_player.y), (2, 1))

    def test_move_rejects_world_boundary_without_changing_state(self):
        self.player.x = 0
        self.player.y = 0
        veilborn_mud.players_in_rooms.clear()
        track_player(self.player, veilborn_mud.players_in_rooms)

        moved = move_player(
            self.player,
            "north",
            self.world_map,
            veilborn_mud.players_in_rooms,
        )

        self.assertFalse(moved)
        self.assertEqual((self.player.x, self.player.y), (0, 0))
        self.assertEqual(veilborn_mud.players_in_rooms[(0, 0)], [self.player])

    def test_move_does_not_change_tracking_when_database_write_is_blocked(self):
        class BlockedCursor:
            connection = self.connection

            def execute(self, query, params):
                raise sqlite3.OperationalError("database is locked")

        self.player.cursor = BlockedCursor()

        with self.assertRaises(LocationPersistenceError):
            move_player(
                self.player,
                "east",
                self.world_map,
                veilborn_mud.players_in_rooms,
            )

        self.assertEqual((self.player.x, self.player.y), (1, 1))
        self.assertEqual(veilborn_mud.players_in_rooms, {(1, 1): [self.player]})

    def test_players_at_uses_coordinate_key(self):
        other = TestProtocol(veilborn_mud.cursor)
        other.username = "Neighbor"
        other.x = 1
        other.y = 1
        track_player(other, veilborn_mud.players_in_rooms)

        self.assertEqual(
            players_at(veilborn_mud.players_in_rooms, 1, 1, exclude=self.player),
            [other],
        )

    def test_nearby_players_orders_nearest_and_excludes_current_location(self):
        same_room = TestProtocol(veilborn_mud.cursor)
        same_room.username = "SameRoom"
        same_room.x = 1
        same_room.y = 1
        nearby = TestProtocol(veilborn_mud.cursor)
        nearby.username = "Nearby"
        nearby.x = 2
        nearby.y = 1
        farther = TestProtocol(veilborn_mud.cursor)
        farther.username = "Farther"
        farther.x = 3
        farther.y = 3
        for player in (same_room, nearby, farther):
            track_player(player, veilborn_mud.players_in_rooms)

        results = nearby_players(
            veilborn_mud.players_in_rooms,
            self.player.x,
            self.player.y,
            2,
            exclude=self.player,
        )

        self.assertEqual(results, [(1, nearby), (2, farther)])

    def test_overlay_lookup_does_not_mutate_terrain(self):
        zone = {
            "name": "Test Town",
            "rooms": {
                "3000": {
                    "description": "Town square",
                    "exits": {},
                    "x_offset": 1,
                    "y_offset": 0,
                }
            },
        }
        original_map = [row[:] for row in self.world_map]

        overlays = utils.overlay_zone(zone, 0, 1)
        location = get_location(self.world_map, 1, 1, overlays)

        self.assertEqual(self.world_map, original_map)
        self.assertEqual(location["terrain"], ".")
        self.assertEqual(location["overlay"]["zone_name"], "Test Town")
        self.assertEqual(location["overlay"]["vnum"], 3000)

    def test_render_open_land_marks_overlay_with_single_character(self):
        overlays = {(2, 1): {"zone_name": "Test Town", "vnum": 3000, "room": {}}}

        rendered = utils.render_open_land(
            1,
            1,
            world_map=self.world_map,
            overlays=overlays,
            width_radius=1,
            height_radius=1,
        )

        self.assertEqual(
            rendered.splitlines(),
            ["...", ".P#", "...", "Legend: P=you  @=player  N=NPC  #=authored area"],
        )

    def test_render_open_land_marks_players_and_npcs(self):
        rendered = utils.render_open_land(
            1,
            1,
            world_map=self.world_map,
            overlays={(2, 1): {"zone_name": "Test Town", "vnum": 3000, "room": {}}},
            width_radius=1,
            height_radius=1,
            player_locations={(0, 1)},
            npc_locations={(1, 0)},
        )

        self.assertEqual(
            rendered.splitlines(),
            [".N.", "@P#", "...", "Legend: P=you  @=player  N=NPC  #=authored area"],
        )

    def test_survey_uses_supported_renderer_arguments(self):
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_survey(self.player)
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map

        self.assertEqual(len(self.player.messages[-1].splitlines()), 18)


if __name__ == "__main__":
    unittest.main()
