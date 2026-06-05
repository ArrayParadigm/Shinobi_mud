"""Combat, stance, and technique commands."""

import general_commands
from commands import command_subset


COMMANDS = command_subset(general_commands, [
    "talk", "consider", "attack", "combat", "stance", "throw",
    "technique", "strike", "guard", "feint", "recover",
])
