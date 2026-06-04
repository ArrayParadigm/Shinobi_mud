import sqlite3
import unittest

import general_commands
import shinobi_mud
import social_commands
from migrations import apply_migrations
from socials import active_social_states
from tests.test_accounts import TestProtocol


class SocialCatalogTests(unittest.TestCase):
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
        for player in (self.array, self.eve):
            player.messages.clear()

    def tearDown(self):
        shinobi_mud.players_in_rooms.clear()
        shinobi_mud.WORLD_OVERLAYS.clear()
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
        player = TestProtocol(self.connection.cursor())
        player.username = username
        player.x = x
        player.y = y
        player.state = "COMMAND"
        player.track_player()
        return player

    def test_socials_list_hides_adult_categories_until_opt_in(self):
        social_commands.handle_socials(self.array, "", [], shinobi_mud.players_in_rooms)

        rendered = "\n".join(self.array.messages)
        self.assertIn("wave", rendered)
        self.assertIn("holdhands", rendered)
        self.assertNotIn("cuddle", rendered)
        self.assertNotIn("tie", rendered)

        self.array.messages.clear()
        social_commands.handle_consent(
            self.array,
            "allow intimate",
            ["allow", "intimate"],
            shinobi_mud.players_in_rooms,
        )
        social_commands.handle_socials(self.array, "", [], shinobi_mud.players_in_rooms)

        rendered = "\n".join(self.array.messages)
        self.assertIn("cuddle", rendered)
        self.assertNotIn("tie", rendered)

    def test_consent_gated_social_refuses_then_delivers(self):
        social_commands.handle_catalog_social(
            self.array,
            "Eve",
            ["Eve"],
            shinobi_mud.players_in_rooms,
            "hug",
        )

        self.assertEqual(self.array.messages, ["Eve has not consented to friendly socials from you."])
        self.assertEqual(self.eve.messages, [])

        social_commands.handle_consent(
            self.eve,
            "allow friendly Array",
            ["allow", "friendly", "Array"],
            shinobi_mud.players_in_rooms,
        )
        self.array.messages.clear()
        self.eve.messages.clear()

        social_commands.handle_catalog_social(
            self.array,
            "Eve",
            ["Eve"],
            shinobi_mud.players_in_rooms,
            "hug",
        )

        self.assertEqual(self.array.messages, ["You hug Eve."])
        self.assertEqual(self.eve.messages, ["Array hugs you."])

    def test_holdhands_leads_consenting_target_on_movement(self):
        for category in ("utility", "mechanical"):
            social_commands.handle_consent(
                self.eve,
                f"allow {category} Array",
                ["allow", category, "Array"],
                shinobi_mud.players_in_rooms,
            )
        self.array.messages.clear()
        self.eve.messages.clear()

        social_commands.handle_catalog_social(
            self.array,
            "Eve",
            ["Eve"],
            shinobi_mud.players_in_rooms,
            "holdhands",
        )

        self.assertEqual(self.array.messages, ["You take Eve's hand."])
        self.assertEqual(self.eve.messages, ["Array takes your hand."])

        original_map = general_commands.UTILITIES["WORLD_MAP"]
        original_render_room = general_commands.UTILITIES["render_room"]
        original_render_open_land = general_commands.UTILITIES["render_open_land"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        general_commands.UTILITIES["render_room"] = lambda player, overlays: None
        general_commands.UTILITIES["render_open_land"] = lambda *args, **kwargs: "map"
        self.array.messages.clear()
        self.eve.messages.clear()
        try:
            general_commands.handle_movement(self.array, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map
            general_commands.UTILITIES["render_room"] = original_render_room
            general_commands.UTILITIES["render_open_land"] = original_render_open_land

        self.assertEqual((self.array.x, self.array.y), (2, 1))
        self.assertEqual((self.eve.x, self.eve.y), (2, 1))
        self.assertIn("You lead Eve east.", self.array.messages)
        self.assertIn("Array leads you east.", self.eve.messages)

    def test_restrictive_social_blocks_movement_until_resisted(self):
        for category in ("bdsm", "restrictive"):
            social_commands.handle_consent(
                self.eve,
                f"allow {category} Array",
                ["allow", category, "Array"],
                shinobi_mud.players_in_rooms,
            )
        social_commands.handle_consent(
            self.array,
            "allow bdsm",
            ["allow", "bdsm"],
            shinobi_mud.players_in_rooms,
        )
        self.array.messages.clear()
        self.eve.messages.clear()

        social_commands.handle_catalog_social(
            self.array,
            "Eve",
            ["Eve"],
            shinobi_mud.players_in_rooms,
            "tie",
        )

        self.assertEqual(self.array.messages, ["You restrain Eve."])
        self.assertEqual(self.eve.messages, ["Array restrains you."])
        self.eve.messages.clear()
        original_map = general_commands.UTILITIES["WORLD_MAP"]
        general_commands.UTILITIES["WORLD_MAP"] = self.world_map
        try:
            general_commands.handle_movement(self.eve, "east")
        finally:
            general_commands.UTILITIES["WORLD_MAP"] = original_map
        self.assertEqual((self.eve.x, self.eve.y), (1, 1))
        self.assertEqual(
            self.eve.messages,
            ["You are restrained by Array. Use resist or ask them to release you."],
        )

        social_commands.handle_resist(self.eve, "", [], shinobi_mud.players_in_rooms)

        self.assertIn("You resist free from the restraint.", self.eve.messages)
        self.assertEqual(active_social_states(self.connection.cursor(), "Eve"), [])


if __name__ == "__main__":
    unittest.main()
