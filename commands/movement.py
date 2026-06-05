"""Movement and world-view commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
    "look", "survey", "loc", "who", "color",
])
