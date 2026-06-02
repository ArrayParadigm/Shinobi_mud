import unittest

from command_system import CommandSpec
import shinobi_mud
from tests.test_accounts import TestProtocol


class CommandResolutionTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = shinobi_mud.COMMAND_REGISTRY.copy()
        self.original_aliases = shinobi_mud.COMMAND_ALIASES.copy()
        self.calls = []
        shinobi_mud.COMMAND_REGISTRY.clear()
        shinobi_mud.COMMAND_ALIASES.clear()
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
        shinobi_mud.COMMAND_ALIASES.clear()
        shinobi_mud.COMMAND_ALIASES.update(self.original_aliases)

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

    def test_command_parsing_accepts_general_whitespace(self):
        shinobi_mud.process_command(self.player, "\tsa\t  hello there  ")

        self.assertEqual(self.calls, [("say", "hello there", ["hello", "there"])])

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


class CommandMetadataTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = shinobi_mud.COMMAND_REGISTRY.copy()
        self.original_aliases = shinobi_mud.COMMAND_ALIASES.copy()
        shinobi_mud.COMMAND_REGISTRY.clear()
        shinobi_mud.load_commands()
        self.player = TestProtocol(None)
        self.player.username = "MetadataUser"

    def tearDown(self):
        shinobi_mud.COMMAND_REGISTRY.clear()
        shinobi_mud.COMMAND_REGISTRY.update(self.original_registry)
        shinobi_mud.COMMAND_ALIASES.clear()
        shinobi_mud.COMMAND_ALIASES.update(self.original_aliases)

    def test_registered_commands_expose_metadata(self):
        for name, command in shinobi_mud.COMMAND_REGISTRY.items():
            with self.subTest(command=name):
                self.assertIsInstance(command, CommandSpec)
                self.assertTrue(command.usage)
                self.assertTrue(command.description)
                self.assertIn(command.permission, {"player", "admin"})

    def test_semantic_alias_resolves_to_canonical_command(self):
        self.assertEqual(shinobi_mud.resolve_command_name("status"), ("score", []))
        self.assertEqual(shinobi_mud.resolve_command_name("stat"), ("score", []))

    def test_usage_validation_happens_before_handler(self):
        shinobi_mud.process_command(self.player, "say")
        shinobi_mud.process_command(self.player, "goto definitely-not-a-room")

        self.assertEqual(
            self.player.messages,
            [
                "Usage: say <message>",
                "You do not have permission to use that command.",
            ],
        )

    def test_admin_argument_validation_returns_usage(self):
        self.player.is_admin = True

        shinobi_mud.process_command(self.player, "goto definitely-not-a-room")

        self.assertEqual(
            self.player.messages,
            ["Usage: goto <vnum> | goto grid <x> <y> | goto player <name>"],
        )

    def test_help_lists_player_commands_without_admin_commands(self):
        shinobi_mud.process_command(self.player, "help")

        command_list = self.player.messages[1]
        self.assertIn("look", command_list)
        self.assertIn("say", command_list)
        self.assertNotIn("shutdown", command_list)

    def test_help_detail_uses_metadata_and_aliases(self):
        shinobi_mud.process_command(self.player, "help stat")

        self.assertEqual(
            self.player.messages,
            [
                "score: Display your character sheet.",
                "Usage: score",
                "Aliases: status",
            ],
        )

    def test_admin_help_includes_admin_commands(self):
        self.player.is_admin = True

        shinobi_mud.process_command(self.player, "help")

        self.assertIn("shutdown", self.player.messages[1])

    def test_commands_catalog_lists_every_command_with_descriptions(self):
        shinobi_mud.process_command(self.player, "commands")

        catalog = "\n".join(self.player.messages)
        self.assertEqual(self.player.messages[0], "Command Catalog")
        self.assertIn("  attack <character> - Strike a hostile character at your location.", catalog)
        self.assertIn("  commands - List every command with a brief description.", catalog)
        self.assertIn("  inventory - List the items you carry. (aliases: inv)", catalog)
        self.assertIn("  shutdown [admin] - Stop the server.", catalog)
        self.assertEqual(self.player.messages[-1], "Use help <command> for detailed usage.")

    def test_commands_catalog_is_complete_for_registered_metadata(self):
        shinobi_mud.process_command(self.player, "commands")

        catalog = "\n".join(self.player.messages)
        for command in shinobi_mud.COMMAND_REGISTRY.values():
            with self.subTest(command=command.name):
                self.assertIn(f"  {command.usage}", catalog)


if __name__ == "__main__":
    unittest.main()
