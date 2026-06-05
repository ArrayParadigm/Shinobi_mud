"""Inventory, item, and consumption commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "inventory", "get", "drop", "examine", "wield", "remove", "eat", "drink",
])
