import sqlite3
import unittest

import general_commands
import shinobi_mud
import utils
from auth import hash_password
from locations import get_location, move_player, players_at, track_player
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        shinobi_mud.conn = self.connection
        shinobi_mud.cursor = self.connection.cursor()
        shinobi_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.world_map = [list("..."), list("..."), list("...")]

        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            ("Walker", "hash", 1, 1),
        )
        self.connection.commit()
        self.player = TestProtocol(shinobi_mud.cursor)
        self.player.username = "Walker"
        self.player.x = 1
        self.player.y = 1
        track_player(self.player, shinobi_mud.players_in_rooms)

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_move_updates_tracking_bucket_and_database(self):
        moved = move_player(
            self.player,
            "east",
            self.world_map,
            shinobi_mud.players_in_rooms,
        )

        self.assertTrue(moved)
        self.assertEqual((self.player.x, self.player.y), (2, 1))
        self.assertNotIn((1, 1), shinobi_mud.players_in_rooms)
        self.assertEqual(shinobi_mud.players_in_rooms[(2, 1)], [self.player])
        coordinates = self.connection.execute(
            "SELECT x, y FROM players WHERE username=?",
            ("Walker",),
        ).fetchone()
        self.assertEqual(tuple(coordinates), (2, 1))

    def test_login_restores_coordinates_saved_by_movement(self):
        self.connection.execute(
            "UPDATE players SET password=? WHERE username=?",
            (hash_password("password"), "Walker"),
        )
        self.connection.commit()
        move_player(self.player, "east", self.world_map, shinobi_mud.players_in_rooms)
        shinobi_mud.players_in_rooms.clear()
        returning_player = TestProtocol(shinobi_mud.cursor)

        returning_player.handle_username("Walker")
        returning_player.handle_password("password")

        self.assertEqual((returning_player.x, returning_player.y), (2, 1))

    def test_move_rejects_world_boundary_without_changing_state(self):
        self.player.x = 0
        self.player.y = 0
        shinobi_mud.players_in_rooms.clear()
        track_player(self.player, shinobi_mud.players_in_rooms)

        moved = move_player(
            self.player,
            "north",
            self.world_map,
            shinobi_mud.players_in_rooms,
        )

        self.assertFalse(moved)
        self.assertEqual((self.player.x, self.player.y), (0, 0))
        self.assertEqual(shinobi_mud.players_in_rooms[(0, 0)], [self.player])

    def test_players_at_uses_coordinate_key(self):
        other = TestProtocol(shinobi_mud.cursor)
        other.username = "Neighbor"
        other.x = 1
        other.y = 1
        track_player(other, shinobi_mud.players_in_rooms)

        self.assertEqual(
            players_at(shinobi_mud.players_in_rooms, 1, 1, exclude=self.player),
            [other],
        )

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

        self.assertEqual(rendered.splitlines(), ["...", ".P#", "..."])

    def test_survey_uses_supported_renderer_arguments(self):
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_survey(self.player)
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map

        self.assertEqual(len(self.player.messages[-1].splitlines()), 11)


if __name__ == "__main__":
    unittest.main()
