import re
import sqlite3
import unittest

import general_commands
import veilborn_mud
import social_commands
import utils
from migrations import apply_migrations
from tests.test_accounts import TestProtocol


ANSI_SEQUENCE = re.compile(r"\x1b\[[0-9;]*m")


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        veilborn_mud.conn = self.connection
        veilborn_mud.cursor = self.connection.cursor()
        veilborn_mud.ensure_tables_exist(self.connection)
        apply_migrations(self.connection)
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.execute(
            "INSERT INTO players (username, password, x, y) VALUES (?, ?, ?, ?)",
            ("ColorUser", "hash", 1, 1),
        )
        self.connection.commit()
        self.player = TestProtocol(veilborn_mud.cursor)
        self.player.username = "ColorUser"
        self.player.x = 1
        self.player.y = 1

    def tearDown(self):
        veilborn_mud.players_in_rooms.clear()
        veilborn_mud.WORLD_OVERLAYS.clear()
        self.connection.close()

    def test_color_command_toggles_session_preference(self):
        general_commands.handle_color(self.player, "on")
        self.assertTrue(self.player.color_enabled)
        self.assertEqual(self.player.messages, ["Color is now on."])

        general_commands.handle_color(self.player, "off")
        self.assertFalse(self.player.color_enabled)
        self.assertEqual(self.player.messages[-1], "Color is now off.")

    def test_plain_prompt_output_is_preserved_when_color_is_off(self):
        self.player.display_prompt()

        self.assertEqual(self.player.messages, ["[HP:10/10 ST:10/10 CH:10/10 | (1, 1)]"])

    def test_colored_prompt_preserves_readable_text(self):
        self.player.color_enabled = True

        self.player.display_prompt()

        rendered = self.player.messages[0]
        self.assertIn("\x1b[", rendered)
        self.assertEqual(
            ANSI_SEQUENCE.sub("", rendered),
            "[HP:10/10 ST:10/10 CH:10/10 | (1, 1)]",
        )

    def test_colored_map_styles_markers_without_changing_plain_text(self):
        world_map = [list("..."), list("..."), list("...")]
        overlays = {(2, 1): {"zone_name": "Test Town", "vnum": 3000, "room": {}}}

        rendered = utils.render_open_land(
            1,
            1,
            world_map=world_map,
            overlays=overlays,
            width_radius=1,
            height_radius=1,
            color_enabled=True,
        )

        self.assertIn("\x1b[", rendered)
        self.assertEqual(
            ANSI_SEQUENCE.sub("", rendered).splitlines(),
            ["...", ".P#", "...", "Legend: P=you  @=player  N=NPC  #=authored area"],
        )

    def test_chat_strips_terminal_control_characters(self):
        veilborn_mud.players_in_rooms[(1, 1)] = [self.player]

        social_commands.handle_say(
            self.player,
            "hello\x1b[31mred",
            ["hello\x1b[31mred"],
            veilborn_mud.players_in_rooms,
        )

        self.assertEqual(self.player.messages, ['ColorUser says, "hellored"'])
        self.assertNotIn("\x1b", self.player.messages[0])


if __name__ == "__main__":
    unittest.main()
