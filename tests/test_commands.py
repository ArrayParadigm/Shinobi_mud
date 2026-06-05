import json
import re
import tempfile
import unittest
from pathlib import Path

from command_system import CommandSpec
from help_content import DEFAULT_CATEGORY_FILE, DEFAULT_HELP_FILE
import veilborn_mud
from tests.test_accounts import TestProtocol


class CommandResolutionTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = veilborn_mud.COMMAND_REGISTRY.copy()
        self.original_aliases = veilborn_mud.COMMAND_ALIASES.copy()
        self.calls = []
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.COMMAND_ALIASES.clear()
        for name in (
            "look",
            "north",
            "south",
            "east",
            "west",
            "northeast",
            "northwest",
            "southeast",
            "southwest",
            "say",
            "score",
            "status",
            "survey",
            "sethouse",
            "setrole",
            "setstat",
        ):
            veilborn_mud.COMMAND_REGISTRY[name] = self.handler_for(name)
        self.player = TestProtocol(None)
        self.player.username = "Resolver"

    def tearDown(self):
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.COMMAND_REGISTRY.update(self.original_registry)
        veilborn_mud.COMMAND_ALIASES.clear()
        veilborn_mud.COMMAND_ALIASES.update(self.original_aliases)

    def handler_for(self, name):
        def handler(player, players_in_rooms, raw_args, split_args):
            self.calls.append((name, raw_args, split_args))

        return handler

    def test_exact_command_wins(self):
        veilborn_mud.process_command(self.player, "status")

        self.assertEqual(self.calls, [("status", "", [])])

    def test_unique_prefix_resolves_command_and_preserves_arguments(self):
        veilborn_mud.process_command(self.player, "eas")
        veilborn_mud.process_command(self.player, "sa hello there")

        self.assertEqual(
            self.calls,
            [("east", "", []), ("say", "hello there", ["hello", "there"])],
        )

    def test_command_parsing_accepts_general_whitespace(self):
        veilborn_mud.process_command(self.player, "\tsa\t  hello there  ")

        self.assertEqual(self.calls, [("say", "hello there", ["hello", "there"])])

    def test_reserved_shortcuts_win_even_when_prefix_is_ambiguous(self):
        for command in ("n", "s", "e", "w", "ne", "nw", "se", "sw", "l"):
            veilborn_mud.process_command(self.player, command)

        self.assertEqual(
            [call[0] for call in self.calls],
            ["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "look"],
        )

    def test_ambiguous_prefix_reports_matches_without_running_command(self):
        veilborn_mud.process_command(self.player, "set")

        self.assertEqual(self.calls, [])
        self.assertEqual(
            self.player.messages,
            ["Ambiguous command 'set': sethouse, setrole, setstat"],
        )

    def test_unknown_command_is_reported(self):
        veilborn_mud.process_command(self.player, "nope")

        self.assertEqual(self.calls, [])
        self.assertEqual(self.player.messages, ["Unknown command: nope"])


class CommandMetadataTests(unittest.TestCase):
    def setUp(self):
        self.original_registry = veilborn_mud.COMMAND_REGISTRY.copy()
        self.original_aliases = veilborn_mud.COMMAND_ALIASES.copy()
        self.original_config = veilborn_mud.ACTIVE_CONFIG.copy()
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.load_commands()
        self.player = TestProtocol(None)
        self.player.username = "MetadataUser"

    def tearDown(self):
        veilborn_mud.COMMAND_REGISTRY.clear()
        veilborn_mud.COMMAND_REGISTRY.update(self.original_registry)
        veilborn_mud.COMMAND_ALIASES.clear()
        veilborn_mud.COMMAND_ALIASES.update(self.original_aliases)
        veilborn_mud.ACTIVE_CONFIG.clear()
        veilborn_mud.ACTIVE_CONFIG.update(self.original_config)

    def test_registered_commands_expose_metadata(self):
        for name, command in veilborn_mud.COMMAND_REGISTRY.items():
            with self.subTest(command=name):
                self.assertIsInstance(command, CommandSpec)
                self.assertTrue(command.usage)
                self.assertTrue(command.description)
                self.assertIn(command.permission, {"player", "builder", "admin"})

    def test_semantic_alias_resolves_to_canonical_command(self):
        self.assertEqual(veilborn_mud.resolve_command_name("status"), ("score", []))
        self.assertEqual(veilborn_mud.resolve_command_name("stat"), ("score", []))
        self.assertEqual(veilborn_mud.resolve_command_name("ne"), ("northeast", []))

    def test_usage_validation_happens_before_handler(self):
        veilborn_mud.process_command(self.player, "say")
        veilborn_mud.process_command(self.player, "goto definitely-not-a-room")

        self.assertEqual(
            self.player.messages,
            [
                "Usage: say <message>",
                "You do not have permission to use that command.",
            ],
        )

    def test_admin_argument_validation_returns_usage(self):
        self.player.is_admin = True

        veilborn_mud.process_command(self.player, "goto definitely-not-a-room")

        self.assertEqual(
            self.player.messages,
            ["Usage: goto <vnum> | goto grid <x> <y> | goto player <name>"],
        )

    def test_builder_argument_validation_returns_usage_for_builder_commands(self):
        self.player.is_builder = True

        veilborn_mud.process_command(self.player, "goto definitely-not-a-room")

        self.assertEqual(
            self.player.messages,
            ["Usage: goto <vnum> | goto grid <x> <y> | goto player <name>"],
        )

    def test_help_lists_player_commands_without_admin_commands(self):
        veilborn_mud.process_command(self.player, "help")

        command_list = "\n".join(self.player.messages)
        self.assertIn("look", command_list)
        self.assertIn("say", command_list)
        self.assertNotIn("buildzone", command_list)
        self.assertNotIn("shutdown", command_list)

    def test_builder_help_includes_builder_commands_without_admin_commands(self):
        self.player.is_builder = True

        veilborn_mud.process_command(self.player, "help")

        command_list = "\n".join(self.player.messages)
        self.assertIn("buildzone", command_list)
        self.assertNotIn("shutdown", command_list)

    def test_help_detail_uses_metadata_and_aliases(self):
        veilborn_mud.process_command(self.player, "help stat")

        self.assertEqual(
            self.player.messages,
            [
                "score: Display your character sheet. (i)",
                "Usage: score",
                "Aliases: status",
                "Shows core resources, attributes, specialty, clan, essence, house alignment, and location.",
            ],
        )

    def test_admin_help_includes_admin_commands(self):
        self.player.is_admin = True

        veilborn_mud.process_command(self.player, "help")

        self.assertIn("shutdown", "\n".join(self.player.messages))

    def test_commands_catalog_lists_every_command_with_descriptions(self):
        veilborn_mud.process_command(self.player, "commands")

        catalog = "\n".join(self.player.messages)
        self.assertEqual(self.player.messages[0], "Command Catalog")
        self.assertIn("== Movement ==", catalog)
        self.assertIn("== Techniques ==", catalog)
        self.assertIn("== Builder ==", catalog)
        self.assertIn("== Admin ==", catalog)
        self.assertIn("  attack <character> - Engage a hostile character for round combat. (i)", catalog)
        self.assertIn("  technique [technique] - List or queue a stamina-based fighting technique. (i)", catalog)
        self.assertIn("  strike - Queue Strike for the next combat round. (i)", catalog)
        self.assertIn("  commands - List every command with a brief description. (i)", catalog)
        self.assertIn("  inventory - List the items you carry. (i) (aliases: inv)", catalog)
        self.assertIn("  buildzone <zone_key> <start_vnum> <end_vnum> <x> <y> <room_title> [builder] - Create, anchor, and enter a usable authored zone. (i)", catalog)
        self.assertIn("  shutdown [admin] - Stop the server. (i)", catalog)
        self.assertEqual(self.player.messages[-1], "Use help <command> for detailed usage.")

    def test_commands_catalog_is_complete_for_registered_metadata(self):
        veilborn_mud.process_command(self.player, "commands")

        catalog = "\n".join(self.player.messages)
        for command in veilborn_mud.COMMAND_REGISTRY.values():
            with self.subTest(command=command.name):
                self.assertIn(f"  {command.usage}", catalog)

    def test_editable_help_catalog_covers_every_registered_command(self):
        catalog = json.loads(Path(DEFAULT_HELP_FILE).read_text(encoding="utf-8"))

        self.assertEqual(set(catalog), set(veilborn_mud.COMMAND_REGISTRY))

    def test_editable_categories_list_every_registered_command_once(self):
        categories = json.loads(Path(DEFAULT_CATEGORY_FILE).read_text(encoding="utf-8"))
        categorized_commands = [
            command
            for commands in categories.values()
            for command in commands
        ]

        self.assertEqual(set(categorized_commands), set(veilborn_mud.COMMAND_REGISTRY))
        self.assertEqual(len(categorized_commands), len(set(categorized_commands)))

    def test_commands_catalog_colors_section_headers_without_changing_text(self):
        self.player.color_enabled = True

        veilborn_mud.process_command(self.player, "commands")

        rendered = "\n".join(self.player.messages)
        self.assertIn("\x1b[", rendered)
        self.assertIn("== Movement ==", re.sub(r"\x1b\[[0-9;]*m", "", rendered))

    def test_invalid_editable_categories_fall_back_to_other_section(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            category_file = Path(temporary_directory) / "categories.json"
            category_file.write_text("{ invalid json", encoding="utf-8")
            veilborn_mud.ACTIVE_CONFIG["command_categories_file"] = str(category_file)

            veilborn_mud.process_command(self.player, "commands")

        self.assertEqual(self.player.messages[1], "== Other ==")
        self.assertIn("  commands - List every command with a brief description. (i)", self.player.messages)

    def test_suggest_and_bug_append_timestamped_feedback_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            suggestions_file = Path(temporary_directory) / "suggestions.md"
            bugs_file = Path(temporary_directory) / "bugs.md"
            veilborn_mud.ACTIVE_CONFIG["suggestions_file"] = str(suggestions_file)
            veilborn_mud.ACTIVE_CONFIG["bugs_file"] = str(bugs_file)

            veilborn_mud.process_command(self.player, "suggest add more builder signs")
            veilborn_mud.process_command(self.player, "bug look map overlaps")
            suggestions_text = suggestions_file.read_text(encoding="utf-8")
            bugs_text = bugs_file.read_text(encoding="utf-8")

        self.assertIn("Suggestion recorded.", self.player.messages)
        self.assertIn("Bug report recorded.", self.player.messages)
        self.assertIn('MetadataUser Suggested at ', suggestions_text)
        self.assertIn('"add more builder signs"', suggestions_text)
        self.assertIn('MetadataUser Reported at ', bugs_text)
        self.assertIn('"look map overlaps"', bugs_text)

    def test_help_prose_refreshes_from_disk_without_reloading_commands(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            help_file = Path(temporary_directory) / "commands.json"
            help_file.write_text(
                json.dumps({"score": {"summary": "First summary.", "details": ["First detail."]}}),
                encoding="utf-8",
            )
            veilborn_mud.ACTIVE_CONFIG["help_file"] = str(help_file)

            veilborn_mud.process_command(self.player, "help score")
            help_file.write_text(
                json.dumps({"score": {"summary": "Updated summary.", "details": ["Updated detail."]}}),
                encoding="utf-8",
            )
            veilborn_mud.process_command(self.player, "help score")

        self.assertIn("score: First summary. (i)", self.player.messages)
        self.assertIn("First detail.", self.player.messages)
        self.assertIn("score: Updated summary. (i)", self.player.messages)
        self.assertIn("Updated detail.", self.player.messages)

    def test_invalid_editable_help_falls_back_to_code_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            help_file = Path(temporary_directory) / "commands.json"
            help_file.write_text("{ invalid json", encoding="utf-8")
            veilborn_mud.ACTIVE_CONFIG["help_file"] = str(help_file)

            veilborn_mud.process_command(self.player, "help score")

        self.assertEqual(
            self.player.messages,
            [
                "score: Display your character sheet. (i)",
                "Usage: score",
                "Aliases: status",
            ],
        )


if __name__ == "__main__":
    unittest.main()
