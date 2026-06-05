"""Help, command discovery, and feedback commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "help", "commands", "suggest", "bug",
])
