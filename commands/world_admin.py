"""Server and world administration commands."""

import admin_commands
from commands import command_subset


COMMANDS = command_subset(admin_commands, [
    "shutdown", "copyover",
])
