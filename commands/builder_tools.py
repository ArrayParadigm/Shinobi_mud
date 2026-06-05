"""Builder room, zone, and template commands."""

import admin_commands
from commands import command_subset


COMMANDS = command_subset(admin_commands, [
    "createzone", "buildzone", "zonelist", "zstat", "rlist", "mlist", "ilist",
    "bfind", "contentcheck", "zpublish", "goto", "zoneinfo", "placezone",
    "reloadcontent", "dig", "roomdesc", "redit", "rstat", "rdelete",
    "createnpc", "medit", "mstat", "spawnnpc", "iedit", "istat", "spawnitem",
    "cloneitem", "clonenpc", "cloneroom", "spawnlist", "despawnitem",
    "despawnnpc", "zdelete", "bundo", "hedit",
])
