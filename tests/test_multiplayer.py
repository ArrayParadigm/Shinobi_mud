import logging
import sqlite3
import unittest

import general_commands
import veilborn_mud
import social_commands
from locations import move_player
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


class MultiplayerTests(unittest.TestCase):
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

        self.array = self.create_player("Array", 1, 1)
        self.eve = self.create_player("Eve", 1, 1)
        self.distant = self.create_player("Distant", 2, 2)
        for player in (self.array, self.eve, self.distant):
            player.messages.clear()

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def create_player(self, username, x, y):
        self.connection.execute(
            """
            INSERT INTO players (username, password, x, y)
            VALUES (?, ?, ?, ?)
            """,
            (username, "hash", x, y),
        )
        self.connection.commit()
        player = TestProtocol(veilborn_mud.cursor)
        player.username = username
        player.x = x
        player.y = y
        player.state = "COMMAND"
        player.track_player()
        return player

    def test_say_emote_and_think_are_local(self):
        social_commands.handle_say(self.array, "hello", ["hello"], veilborn_mud.players_in_rooms)
        social_commands.handle_emote(self.array, "waves", ["waves"], veilborn_mud.players_in_rooms)
        social_commands.handle_think(self.array, "", [], veilborn_mud.players_in_rooms)

        self.assertIn('Array says, "hello"', self.array.messages)
        self.assertIn('Array says, "hello"', self.eve.messages)
        self.assertIn("Array waves", self.eve.messages)
        self.assertIn("Array thinks deeply.", self.eve.messages)
        self.assertEqual(self.distant.messages, [])

    def test_ooc_is_global_and_delivered_once(self):
        social_commands.handle_ooc(self.array, "server test", ["server", "test"], veilborn_mud.players_in_rooms)

        for player in (self.array, self.eve, self.distant):
            self.assertEqual(player.messages, ["[OOC] Array: server test"])

    def test_whisper_is_private_and_accepts_online_targets(self):
        social_commands.handle_whisper(
            self.array,
            "Distant quiet words",
            ["Distant", "quiet", "words"],
            veilborn_mud.players_in_rooms,
        )

        self.assertEqual(self.array.messages, ["[Whisper] to Distant: quiet words"])
        self.assertEqual(self.distant.messages, ["[Whisper] from Array: quiet words"])
        self.assertEqual(self.eve.messages, [])

    def test_shout_reaches_adjacent_characters_but_not_farther_ones(self):
        farther = self.create_player("Farther", 3, 3)
        farther.messages.clear()

        social_commands.handle_shout(
            self.array,
            "training begins",
            ["training", "begins"],
            veilborn_mud.players_in_rooms,
        )

        self.assertEqual(self.array.messages, ['Array shouts, "training begins"'])
        self.assertEqual(self.eve.messages, ['Array shouts, "training begins"'])
        self.assertEqual(self.distant.messages, ['Array shouts, "training begins"'])
        self.assertEqual(farther.messages, [])

    def test_whisper_and_shout_strip_terminal_control_sequences(self):
        social_commands.handle_whisper(
            self.array,
            "Distant \x1b[31mquiet\x1b[0m",
            ["Distant", "\x1b[31mquiet\x1b[0m"],
            veilborn_mud.players_in_rooms,
        )
        social_commands.handle_shout(
            self.array,
            "\x1b[31mtraining\x1b[0m",
            ["\x1b[31mtraining\x1b[0m"],
            veilborn_mud.players_in_rooms,
        )

        self.assertEqual(self.array.messages[0], "[Whisper] to Distant: quiet")
        self.assertEqual(self.distant.messages[0], "[Whisper] from Array: quiet")
        self.assertNotIn("\x1b", "".join(self.array.messages + self.distant.messages))

    def test_chat_logs_action_without_message_text(self):
        with self.assertLogs(level=logging.INFO) as captured:
            social_commands.handle_ooc(
                self.array,
                "private-ish words",
                ["private-ish", "words"],
                veilborn_mud.players_in_rooms,
            )

        logs = "\n".join(captured.output)
        self.assertIn("Player Array used ooc", logs)
        self.assertNotIn("private-ish words", logs)

    def test_tracking_announces_arrival_and_disconnect_cleans_up(self):
        newcomer = self.create_player("Newcomer", 1, 1)

        self.assertIn("Newcomer has arrived.", self.array.messages)
        newcomer.connectionLost("test disconnect")

        self.assertNotIn(newcomer, veilborn_mud.players_in_rooms[(1, 1)])
        self.assertIn("Newcomer has left.", self.array.messages)

    def test_movement_announces_departure_and_arrival(self):
        moved = move_player(self.array, "east", self.world_map, veilborn_mud.players_in_rooms)

        self.assertTrue(moved)
        self.assertIn("Array leaves east.", self.eve.messages)
        self.assertEqual((self.array.x, self.array.y), (2, 1))

        arrival_observer = self.create_player("Observer", 1, 1)
        arrival_observer.messages.clear()
        move_player(arrival_observer, "east", self.world_map, veilborn_mud.players_in_rooms)
        self.assertIn("Observer arrives.", self.array.messages)

    def test_movement_lists_players_already_at_destination(self):
        waiting_player = self.create_player("Waiting", 2, 1)
        self.array.messages.clear()
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_movement(self.array, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map

        self.assertIn("Also here: Waiting", self.array.messages)
        self.assertEqual(
            self.array.messages[-1],
            "Nearby: Distant (2, 2; 1 away), Eve (1, 1; 1 away)",
        )
        self.assertIn("-- Nearby --", self.array.messages)
        self.assertIn("Array arrives.", waiting_player.messages)

    def test_room_display_lists_players_already_present(self):
        original_map = veilborn_mud.WORLD_MAP
        veilborn_mud.WORLD_MAP = self.world_map
        try:
            veilborn_mud.VeilbornMUDProtocol.display_room(self.array)
        finally:
            veilborn_mud.WORLD_MAP = original_map

        self.assertIn("Also here: Eve", self.array.messages)
        self.assertIn("-- Nearby --", self.array.messages)
        self.assertEqual(self.array.messages[-1], "Nearby: Distant (2, 2; 1 away)")

    def test_movement_reports_database_lock_without_moving_player(self):
        class BlockedCursor:
            connection = self.connection

            def execute(self, query, params):
                raise sqlite3.OperationalError("database is locked")

        self.array.cursor = BlockedCursor()
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_movement(self.array, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map

        self.assertEqual(
            self.array.messages,
            ["Movement could not be saved. Please try again."],
        )
        self.assertEqual((self.array.x, self.array.y), (1, 1))
        self.assertNotIn("Array leaves east.", self.eve.messages)

    def test_who_lists_each_online_player(self):
        general_commands.handle_who(self.array, veilborn_mud.players_in_rooms)

        self.assertEqual(self.array.messages[0], "Players online: 3")
        self.assertEqual(self.array.messages[1:], ["  Array", "  Distant", "  Eve"])

    def test_score_displays_character_sheet(self):
        veilborn_mud.WORLD_OVERLAYS[(1, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {},
        }

        general_commands.handle_score(self.array)

        self.assertEqual(self.array.messages[0], "Score for Array")
        self.assertIn("Health: 10/10", self.array.messages)
        self.assertIn("Stamina: 10/10", self.array.messages)
        self.assertIn("Wisp: 10/10", self.array.messages)
        self.assertIn("Fatigue: fresh", self.array.messages)
        self.assertIn("Strength: 10  Intellect: 10  Dexterity: 10  Agility: 10  Condition: 10", self.array.messages)
        self.assertIn("Description: An undescribed veilborn stands here.", self.array.messages)
        self.assertIn(
                "Specialty: newbie  Clan: Unaffiliated  Essence: Undeclared",
            self.array.messages,
        )
        self.assertIn("Location: (1, 1)", self.array.messages)
        self.assertIn("Stance: S3 - Balance", self.array.messages)
        self.assertIn("Area: Test Town  VNUM: 3000", self.array.messages)

    def test_prompt_displays_resources_and_overlay_location(self):
        veilborn_mud.WORLD_OVERLAYS[(1, 1)] = {
            "zone_name": "Test Town",
            "vnum": 3000,
            "room": {},
        }

        self.array.display_prompt()

        self.assertEqual(
            self.array.messages,
            ["[HP:10/10 ST:10/10 CH:10/10 | Test Town [3000] (1, 1)]"],
        )

    def test_nearby_player_listing_shows_distance_but_not_roommates(self):
        veilborn_mud.NEARBY_PLAYER_RADIUS = 20

        self.array.list_nearby_players()

        self.assertEqual(self.array.messages, ["Nearby: Distant (2, 2; 1 away)"])

    def test_nearby_player_listing_can_be_disabled(self):
        original_setting = veilborn_mud.SHOW_NEARBY_PLAYERS
        veilborn_mud.SHOW_NEARBY_PLAYERS = False
        try:
            self.array.list_nearby_players()
        finally:
            veilborn_mud.SHOW_NEARBY_PLAYERS = original_setting

        self.assertEqual(self.array.messages, [])

    def test_loc_displays_grid_and_optional_overlay(self):
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_loc(self.array)
            self.assertEqual(self.array.messages, ["Location: (1, 1)", "Terrain: ."])

            self.array.messages.clear()
            veilborn_mud.WORLD_OVERLAYS[(1, 1)] = {
                "zone_name": "Test Town",
                "vnum": 3000,
                "room": {},
            }
            general_commands.handle_loc(self.array)
            self.assertEqual(
                self.array.messages,
                ["Location: (1, 1)", "Area: Test Town  VNUM: 3000"],
            )
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map


if __name__ == "__main__":
    unittest.main()
