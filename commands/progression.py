"""Skill and expression progression commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "prac", "train", "skill", "expression", "useexpression",
])
