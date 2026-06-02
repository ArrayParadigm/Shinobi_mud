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

### Creating a Character

New characters choose a specialty, clan, and natural release after setting a password. Stat allocation is entered once as five named bonuses totaling exactly 10:

```text
strength=2 dexterity=2 agility=2 intelligence=2 wisdom=2
```

Every attribute starts at 5 before those bonuses are applied.

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

The server keeps one maintenance SQLite connection for startup work, authored-content reloads, validation, and scheduled world ticks. Each connected player session receives its own SQLite connection and closes it on disconnect.

For a basic private Linux deployment, follow [LINUX_ALPHA.md](LINUX_ALPHA.md).

### World Locations

The world map is persistent terrain. Player positions use `(x, y)` coordinates as the single source of truth.

Authored cities, dungeons, and other zones can be attached as optional overlays keyed by coordinates. Overlay metadata may include a zone name, VNUM, and room description without replacing or mutating the terrain underneath. This keeps open-world movement consistent while leaving room for drop-in areas later.

Eve's Haven is the first complete overlay example. Its anchor and room offsets live in `zones/eveshaven.json`; startup loads its 30 authored rooms over the wilderness around `(500, 500)`.

### Player Commands

- `look [at <item>]`: display a compact local terrain view or inspect an item.
- `survey`: display the larger terrain view.
- `color <on|off>`: toggle ANSI terminal colors for the current connection.
- `north`, `south`, `east`, `west`: move across the world grid.
- `loc`: display your grid coordinates and optional overlay area.
- `score`: display your character sheet. `status` remains available as an alias.
- `body`: display nutrition, hydration, fatigue, and short-rest chakra recovery.
- `rest`: recover stamina and chakra while reducing fatigue.
- `inventory`: list persistent carried and equipped items. `inv` remains available as an alias.
- `get <item>`: pick up an item at your grid location.
- `drop <item>`: drop a carried item at your grid location.
- `examine <item>`: inspect an item in the room or your inventory.
- `wield <item>`: equip a carried item in its authored slot.
- `remove <item>`: unequip a carried item.
- `eat <item>`: consume a carried food item to restore nutrition.
- `drink <item>`: consume a carried beverage to restore hydration.
- `prac [skill]`: list ordinary skills or inspect one skill's proficiency.
- `train [jutsu]`: list jutsus or inspect one jutsu's proficiency.
- `skill [all|skill]`: list available skills, inspect one, or show the full skill catalog.
- `jutsu [all|jutsu]`: list available jutsus, inspect one, or show the full jutsu catalog.
- `usejutsu <jutsu>`: activate an implemented jutsu.
- `talk <character>`: speak with an NPC at your grid location.
- `consider <character>`: inspect a visible character's combat details.
- `attack <character>`: resolve one melee turn against a hostile NPC at your grid location.
- `throw <item> at <character>`: throw a carried ranged item at a hostile NPC in your room or one cardinal step away.
- `who`: list connected characters.
- `say <message>`: speak to characters at your grid location.
- `whisper <character> <message>`: privately message an online character.
- `shout <message>`: speak to characters at your location and adjacent grid coordinates.
- `emote <action>`: perform an action at your grid location.
- `think`: perform the built-in thinking emote at your grid location.
- `ooc <message>`: speak on the global out-of-character channel.
- `help [command]`: list available commands or display usage details.

Commands accept unique prefixes. The stable shortcuts `n`, `s`, `e`, `w`, and `l` always mean `north`, `south`, `east`, `west`, and `look`. Ambiguous prefixes list their possible matches instead of guessing.

Item targets accept authored keywords and abbreviations. Exact names win first; otherwise the first stable matching instance is used. Use an ordinal such as `get 2.kun` when duplicate items need an explicit selection.

Admin overlay tools:

- `goto <vnum>`: teleport to an authored overlay room while retaining canonical coordinates.
- `goto grid <x> <y>`: teleport to canonical world coordinates.
- `goto player <name>`: teleport to an online character.
- `zoneinfo [vnum]`: inspect the current or requested overlay room.
- `placezone <zone_file> <x> <y>`: persist a zone anchor and reload overlays.
- `reloadcontent`: import authored JSON template changes and missing spawns into live state.
- `dig <direction> <room_name>`: create a coordinate-aware authored room and reciprocal exit.
- `roomdesc <description>`: replace the current authored room description.
- `createnpc <npc_key> <name>`: create a basic static authored NPC template in the current zone.
- `spawnnpc <npc_key>`: persist and import an authored NPC spawn in the current room.
- `copyover`: report that soft restarts are intentionally disabled for now.

The player prompt reports current and maximum health, stamina, chakra, and location after commands. Map output includes a legend. Nearby-character listings are controlled by `show_nearby_players` and `nearby_player_radius` in `config.json`.

ANSI terminal colors are enabled for new connections by default. Set `default_color_enabled` in `config.json` to change the server default, or use `color off` for clients that do not render ANSI colors cleanly.

Room items, character inventories, equipped slots, and NPC instances persist in SQLite. Authored templates, item keywords, equipment metadata, and initial VNUM placements live in zone JSON files such as `zones/eveshaven.json`. Startup imports missing spawns once, so picked-up items are not recreated on every restart.

Eve's Haven authors a Haven Map, Travel Ration, and Water Flask at its entrance, a Practice Kunai in its garden, a Crystal Token in its library, a Haven Guide NPC at the entrance, and a hostile Practice Construct in the garden. `reloadcontent` lets an admin apply JSON template edits and create newly-authored spawns without restarting the server.

Eve's Haven is also the compact training loop. Pick up food and water at the entrance, move north into the garden for the Practice Kunai and Practice Construct, then exercise melee, `throw`, `usejutsu substitution`, `body`, and `rest`.

The combat loop is command-driven and turn-based. `attack <character>` resolves player dexterity against authored NPC evasion, applies strength-based damage plus equipped-weapon metadata on a hit, then resolves a surviving hostile NPC's authored accuracy against player agility. Roommates see the exchange. Defeated NPCs disappear until their authored respawn delay elapses. A defeated player recovers to maximum health at the same grid coordinate.

Characters also have abstract body resources: nutrition, hydration, and fatigue. Ordinary movement and hostile combat increase fatigue. `rest` reduces fatigue, consumes a small amount of nutrition and hydration, restores stamina, and restores chakra based on wisdom and current body condition. Rest is blocked at zero nutrition or hydration. `eat` and `drink` consume finite authored supplies to restore body resources.

Skills and jutsus have separate authored definitions and persistent `0-100%` proficiency. `prac`, `train`, `skill`, and `jutsu` list available records. `skill all` and `jutsu all` expose the wider authored catalog, with future records marked `[unimplemented]`. Valid gameplay use raises proficiency through an authored usage gain; the visible tiers are `Novice`, `Adept`, `Skilled`, `Master`, and `Grandmaster`.

`throw <item> at <character>` is the first real skill action. A valid throw accepts a carried authored item with ranged damage, targets a hostile NPC in the current room or one cardinal step away, adds `2` fatigue, lands the item at the target location, and raises `Throw` proficiency even when the attack misses. The Practice Kunai deals `3` thrown damage.

`usejutsu substitution` prepares Substitution Technique for `30` seconds at a cost of `3` chakra. The next eligible hostile NPC strike during that window is avoided, successful resolution raises Substitution proficiency, and the technique then remains on a persisted `60` second cooldown.

### Early Linux Testing

The current MUD socket uses plain-text TCP. Passwords are hashed safely in the database, but they are still sent over the network as plain text during login. Encrypted transport means wrapping that connection in TLS, or keeping it inside a trusted VPN, so someone watching network traffic cannot read login passwords.

For early Linux testing, restrict access with a firewall allowlist, private network, or VPN. Do not expose password login to the open internet until encrypted transport is added.
