import sqlite3
import unittest
from unittest.mock import patch

import admin_commands
import general_commands
import shinobi_mud
import social_commands
from character_state import feature_state, injury_rows
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


class CharacterStateTests(unittest.TestCase):
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
        self.array = self.create_player("Array", 1, 1)
        self.eve = self.create_player("Eve", 1, 1)
        self.admin = self.create_player("Admin", 0, 0)
        self.admin.is_admin = True
        for player in (self.array, self.eve, self.admin):
            player.messages.clear()

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def create_player(self, username, x, y):
        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            (username, "hash", x, y),
        )
        self.connection.commit()
        player = TestProtocol(self.connection.cursor())
        player.username = username
        player.x = x
        player.y = y
        player.state = "COMMAND"
        player.track_player()
        return player

    def test_migration_adds_safe_character_state_defaults(self):
        row = feature_state(self.connection.cursor(), "Array")

        self.assertEqual(row["hair"], "unspecified")
        self.assertEqual(row["height"], "medium")
        self.assertEqual(row["reproductive_role"], "none")
        self.assertEqual(row["pregnancy_status"], "none")
        self.assertEqual(injury_rows(self.connection.cursor(), "Array"), [])

    def test_features_and_look_at_player_show_public_state(self):
        general_commands.handle_features(self.eve, "hair black",)
        general_commands.handle_features(self.eve, "eyes green",)
        admin_commands.pset(self.admin, "Eve", "injury", "add missing_left_leg")
        admin_commands.pset(self.admin, "Eve", "pregnancy_status", "pregnant")
        admin_commands.pset(self.admin, "Eve", "pregnancy_stage", "middle")
        self.array.messages.clear()

        general_commands.handle_look(self.array, shinobi_mud.players_in_rooms, "at Eve")

        rendered = "\n".join(self.array.messages)
        self.assertIn("You see Eve.", rendered)
        self.assertIn("hair=black", rendered)
        self.assertIn("eyes=green", rendered)
        self.assertIn("missing left leg", rendered)
        self.assertIn("Pregnancy: visibly middle stage.", rendered)
        self.assertNotIn("cycle", rendered.lower())
        self.assertNotIn("reproductive", rendered.lower())

    def test_pregnancy_roll_requires_consent_biology_and_fertile_window(self):
        admin_commands.pset(self.admin, "Array", "repro", "can_impregnate")
        admin_commands.pset(self.admin, "Eve", "repro", "can_carry")
        admin_commands.pset(self.admin, "Eve", "cycle_day", "14")
        for category in ("intimate",):
            social_commands.handle_consent(self.eve, f"allow {category} Array", ["allow", category, "Array"], shinobi_mud.players_in_rooms)
        social_commands.handle_consent(self.array, "allow intimate", ["allow", "intimate"], shinobi_mud.players_in_rooms)
        self.array.messages.clear()
        self.eve.messages.clear()

        with patch("character_state.random.randint", return_value=1):
            social_commands.handle_catalog_social(self.array, "Eve", ["Eve"], shinobi_mud.players_in_rooms, "breed")

        row = feature_state(self.connection.cursor(), "Eve")
        self.assertEqual(row["pregnancy_status"], "pregnant")
        self.assertEqual(row["pregnancy_partner"], "Array")
        self.assertIn("lasting consequences", "\n".join(self.eve.messages))

    def test_injury_penalties_block_movement_and_speech_until_treated(self):
        admin_commands.pset(self.admin, "Eve", "injury", "add missing_left_leg")
        admin_commands.pset(self.admin, "Eve", "injury", "add gagged")
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_movement(self.eve, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map
        social_commands.handle_say(self.eve, "hello", ["hello"], shinobi_mud.players_in_rooms)

        self.assertTrue(any("Your injuries prevent ordinary movement." in message for message in self.eve.messages))
        self.assertIn("You cannot speak clearly right now.", self.eve.messages)

        admin_commands.treatinjury(self.admin, "Eve", "all")
        self.eve.messages.clear()
        social_commands.handle_say(self.eve, "hello", ["hello"], shinobi_mud.players_in_rooms)
        self.assertIn('Eve says, "hello"', self.eve.messages)

    def test_carry_can_move_injured_target_with_consent(self):
        admin_commands.pset(self.admin, "Eve", "injury", "add missing_left_leg")
        for category in ("utility", "mechanical"):
            social_commands.handle_consent(self.eve, f"allow {category} Array", ["allow", category, "Array"], shinobi_mud.players_in_rooms)
        self.array.messages.clear()
        self.eve.messages.clear()

        social_commands.handle_catalog_social(self.array, "Eve", ["Eve"], shinobi_mud.players_in_rooms, "carry")

        original_map = general_commands.UTILITIES["WORLD_MAP"]
        original_render_room = general_commands.UTILITIES["render_room"]
        original_render_open_land = general_commands.UTILITIES["render_open_land"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        general_commands.UTILITIES["render_room"] = lambda player, overlays: None
        general_commands.UTILITIES["render_open_land"] = lambda *args, **kwargs: "map"
        try:
            general_commands.handle_movement(self.array, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map
            general_commands.UTILITIES["render_room"] = original_render_room
            general_commands.UTILITIES["render_open_land"] = original_render_open_land

        self.assertEqual((self.eve.x, self.eve.y), (2, 1))
        self.assertIn("Array moves you east.", self.eve.messages)


if __name__ == "__main__":
    unittest.main()
