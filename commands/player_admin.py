"""Player administration commands."""

import admin_commands
from commands import command_subset


COMMANDS = command_subset(admin_commands, [
    "players", "finger", "pstat", "pset", "pedit", "treatinjury",
    "setrole", "setstat", "sethouse",
])
