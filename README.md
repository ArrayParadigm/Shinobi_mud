# Shinobi_mud

**Shinobi_mud** is a text-based Multi-User Dungeon (MUD) game inspired by the Naruto universe. The current private-alpha foundation supports accounts, multiplayer exploration, chat, and authored zones over a persistent wilderness grid.

The active implementation queue lives in [TODO.md](TODO.md). Older documents under `Content/` are design references for the larger vision.

## Features

- **Command System:** Separate modules for general, admin, and social commands.
- **Dynamic Zones:** Explore various areas and interact with the environment.
- **Multiplayer Support:** Engage with other players in real time.
- **Roleplay Elements:** Embrace your inner shinobi with unique abilities and narrative-driven gameplay.

## Getting Started

### Prerequisites

- **Python 3.8+**
- Linux, macOS, or Windows with terminal support for Python scripts.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ArrayParadigm/Shinobi_mud.git
   cd Shinobi_mud
   ```
2. Create and activate a virtual environment:

   Linux or macOS:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   python shinobi_mud.py
   ```

### Disposable Development Database

The SQLite database is local runtime state and is intentionally not committed to Git. Starting the server creates the configured `shinobi_mud.db` database if it does not exist.

To start again with an empty development database:

```bash
python reset_dev_db.py
```

The reset helper moves the current database into `.local/db_backups/` before the next server launch creates a fresh one. This keeps test characters and experiments disposable while leaving a local recovery copy available when needed.

### Database Migrations

The server applies versioned SQLite migrations during startup. To apply migrations without starting the server:

```bash
python update_schema.py
```

### Promoting an Admin

New accounts are non-admin by default. After creating the first local account, promote it intentionally from the server terminal:

```bash
python promote_admin.py YourUsername
```

Restart the MUD or reconnect that character after promotion.

### Testing

Run the automated test suite from the project root:

```bash
python -m unittest discover -s tests -v
```

The tests use temporary or in-memory databases. They do not modify your local character database.

### Local Development Workflow

For a clean local test cycle:

```bash
python reset_dev_db.py
python -m unittest discover -s tests -v
python shinobi_mud.py
```

The server reads its TCP port from `config.json`.

Each launch writes a timestamped runtime log under `logs/`. These local logs are ignored by Git and include command activity, warnings, and exception tracebacks for debugging.

For a basic private Linux deployment, follow [LINUX_ALPHA.md](LINUX_ALPHA.md).

### World Locations

The world map is persistent terrain. Player positions use `(x, y)` coordinates as the single source of truth.

Authored cities, dungeons, and other zones can be attached as optional overlays keyed by coordinates. Overlay metadata may include a zone name, VNUM, and room description without replacing or mutating the terrain underneath. This keeps open-world movement consistent while leaving room for drop-in areas later.

Eve's Haven is the first complete overlay example. Its anchor and room offsets live in `zones/eveshaven.json`; startup loads its 30 authored rooms over the wilderness around `(500, 500)`.

### Player Commands

- `look`: display nearby terrain and players at your location.
- `survey`: display a compact terrain view.
- `north`, `south`, `east`, `west`: move across the world grid.
- `loc`: display your grid coordinates and optional overlay area.
- `score`: display your character sheet. `status` remains available as an alias.
- `inventory`: list persistent carried items. `inv` remains available as an alias.
- `get <item>`: pick up an item at your grid location.
- `drop <item>`: drop a carried item at your grid location.
- `talk <character>`: speak with an NPC at your grid location.
- `attack <character>`: resolve one melee turn against a hostile NPC at your grid location.
- `who`: list connected characters.
- `say <message>`: speak to characters at your grid location.
- `emote <action>`: perform an action at your grid location.
- `think`: perform the built-in thinking emote at your grid location.
- `ooc <message>`: speak on the global out-of-character channel.
- `help [command]`: list available commands or display usage details.

Commands accept unique prefixes. The stable shortcuts `n`, `s`, `e`, `w`, and `l` always mean `north`, `south`, `east`, `west`, and `look`. Ambiguous prefixes list their possible matches instead of guessing.

Admin overlay tools:

- `goto <vnum>`: teleport to an authored overlay room while retaining canonical coordinates.
- `goto grid <x> <y>`: teleport to canonical world coordinates.
- `goto player <name>`: teleport to an online character.
- `zoneinfo [vnum]`: inspect the current or requested overlay room.
- `placezone <zone_file> <x> <y>`: persist a zone anchor and reload overlays.
- `reloadcontent`: import authored JSON template changes and missing spawns into live state.
- `copyover`: report that soft restarts are intentionally disabled for now.

The player prompt reports health, stamina, chakra, and location after commands. Map output includes a legend. Nearby-character listings are controlled by `show_nearby_players` and `nearby_player_radius` in `config.json`.

Room items, character inventories, and NPC instances persist in SQLite. Authored templates and initial VNUM placements live in zone JSON files such as `zones/eveshaven.json`. Startup imports missing spawns once, so picked-up items are not recreated on every restart.

Eve's Haven authors a Haven Map at its entrance, a Practice Kunai in its garden, a Crystal Token in its library, a Haven Guide NPC at the entrance, and a hostile Practice Construct in the garden. `reloadcontent` lets an admin apply JSON template edits and create newly-authored spawns without restarting the server.

The first combat loop is command-driven and turn-based. `attack <character>` applies strength-based player damage, then a surviving hostile NPC immediately counterattacks. Defeated NPCs disappear until their authored respawn delay elapses; player defeat recovers the character to 10 health.

### Early Linux Testing

The current MUD socket uses plain-text TCP. Passwords are hashed safely in the database, but they are still sent over the network as plain text during login. Encrypted transport means wrapping that connection in TLS, or keeping it inside a trusted VPN, so someone watching network traffic cannot read login passwords.

For early Linux testing, restrict access with a firewall allowlist, private network, or VPN. Do not expose password login to the open internet until encrypted transport is added.
