"""Body, identity, and character-state commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "score", "description", "features", "injuries", "pregnancy", "body", "rest",
])
