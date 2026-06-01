import unittest

import shinobi_mud
from tests.test_accounts import TestProtocol


class CommandResolutionTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = shinobi_mud.COMMAND_REGISTRY.copy()
        self.calls = []
        shinobi_mud.COMMAND_REGISTRY.clear()
        for name in (
            "look",
            "north",
            "south",
            "east",
            "west",
            "say",
            "score",
            "status",
            "survey",
            "setdojo",
            "setrole",
            "setstat",
        ):
            shinobi_mud.COMMAND_REGISTRY[name] = self.handler_for(name)
        self.player = TestProtocol(None)
        self.player.username = "Resolver"

    def tearDown(self):
        shinobi_mud.COMMAND_REGISTRY.clear()
        shinobi_mud.COMMAND_REGISTRY.update(self.original_registry)

    def handler_for(self, name):
        def handler(player, players_in_rooms, raw_args, split_args):
            self.calls.append((name, raw_args, split_args))

        return handler

    def test_exact_command_wins(self):
        shinobi_mud.process_command(self.player, "status")

        self.assertEqual(self.calls, [("status", "", [])])

    def test_unique_prefix_resolves_command_and_preserves_arguments(self):
        shinobi_mud.process_command(self.player, "eas")
        shinobi_mud.process_command(self.player, "sa hello there")

        self.assertEqual(
            self.calls,
            [("east", "", []), ("say", "hello there", ["hello", "there"])],
        )

    def test_reserved_shortcuts_win_even_when_prefix_is_ambiguous(self):
        for command in ("n", "s", "e", "w", "l"):
            shinobi_mud.process_command(self.player, command)

        self.assertEqual(
            [call[0] for call in self.calls],
            ["north", "south", "east", "west", "look"],
        )

    def test_ambiguous_prefix_reports_matches_without_running_command(self):
        shinobi_mud.process_command(self.player, "set")

        self.assertEqual(self.calls, [])
        self.assertEqual(
            self.player.messages,
            ["Ambiguous command 'set': setdojo, setrole, setstat"],
        )

    def test_unknown_command_is_reported(self):
        shinobi_mud.process_command(self.player, "nope")

        self.assertEqual(self.calls, [])
        self.assertEqual(self.player.messages, ["Unknown command: nope"])


if __name__ == "__main__":
    unittest.main()
