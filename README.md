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

### Soak Harness

Run the local private-alpha soak harness before widening the feature surface:

```bash
python soak_harness.py
```

The harness launches a temporary local server, exercises two-client login, movement, chat, combat, reconnect takeover, `prac`, `train`, `body`, and `rest`, then runs a builder smoke path. Transcripts, runtime logs, and the throwaway SQLite database are written under `.local/soak/`.

### Promoting an Admin

New accounts are non-admin by default. After creating the first local account, promote it intentionally from the server terminal:

```bash
python promote_admin.py YourUsername
```

Restart the MUD or reconnect that character after promotion.

### Creating a Character

New characters enter the game immediately after username and password setup. Specialty, clan, release, and descriptive character work are intentionally left blank/default for later systems. Core attributes start at `10` for now.

If the same character logs in again while already connected, the new session takes over the body and the old session is disconnected from active play.

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

The authored `aexpanse` overlay is anchored at `(1, 1)` with two rooms and a seeded Living Void NPC.

### Player Commands

- `look [at <item>]`: display a compact local terrain view or inspect an item.
- `survey`: display the larger terrain view.
- `color <on|off>`: toggle ANSI terminal colors for the current connection.
- `north`, `south`, `east`, `west`, `northeast`, `northwest`, `southeast`, `southwest`: move across the world grid. Diagonal aliases are `ne`, `nw`, `se`, and `sw`.
- `loc`: display your grid coordinates and optional overlay area.
- `score`: display vertical resources, qualitative fatigue, horizontal stats, description, identity, stance, and location. `status` remains available as an alias.
- `description [text]`: view or update your public character description. `desc` remains available as an alias.
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
- `prac [skill]`: list ordinary skills or practice one skill for point-based progression.
- `train [jutsu]`: list jutsus or train one jutsu for point-based progression.
- `skill [all|skill]`: list available skills, inspect one, or show the full skill catalog.
- `jutsu [all|jutsu]`: list available jutsus, inspect one, or show the full jutsu catalog.
- `usejutsu <jutsu>`: activate an implemented jutsu.
- `talk <character>`: speak with an NPC at your grid location.
- `consider <character>`: inspect a visible character's combat details.
- `attack <character>`: engage a hostile NPC at your grid location for round combat.
- `combat`: inspect your engagement, range, queued modifier, and active stance.
- `stance [s1|s2|s3|s4|s5]`: list or change your placeholder combat stance.
- `throw <item> at <character>`: throw a carried ranged item at a hostile NPC in your room or one cardinal step away.
- `who`: list connected characters.
- `say <message>`: speak to characters at your grid location.
- `whisper <character> <message>`: privately message an online character.
- `shout <message>`: speak to characters at your location and adjacent grid coordinates.
- `emote <action>`: perform an action at your grid location.
- `think`: perform the built-in thinking emote at your grid location.
- `socials [category|all]`: list catalog-backed social actions; opt-in adult categories are hidden from the default list.
- `consent [allow|deny <category> [character] | revoke <character>]`: manage social consent for categories such as friendly, playful, intimate, BDSM, mechanical, and restrictive.
- `wave`, `smile`, `nod`, `bow`, `laugh`, `highfive`, `poke`: perform simple social actions.
- `hug`, `pat`, `cuddle`, `nuzzle`: perform consent-gated social actions. Intimate socials require opt-in before use.
- `holdhands <character>`: create a consent-gated handholding state. When you move, the held character is led along if the destination is valid.
- `tie <character>` and `restrain <character>`: create opt-in adult restrictive states that block movement until `release` or `resist`.
- `release <character|all>` and `resist`: end active social holds or restraints. Consent can always be withdrawn or resisted.
- `ooc <message>`: speak on the global out-of-character channel.
- `suggest <message>`: append a timestamped player suggestion to `suggestions.md`.
- `bug <message>`: append a timestamped bug report to `bugs.md`.
- `help [command]`: list available commands or display usage details.
- `commands`: list every player and admin command with its usage and a brief description.

Commands accept unique prefixes. The stable shortcuts `n`, `s`, `e`, `w`, `ne`, `nw`, `se`, `sw`, and `l` always mean their matching movement command or `look`. Ambiguous prefixes list their possible matches instead of guessing.

Item targets accept authored keywords and abbreviations. Exact names win first; otherwise the first stable matching instance is used. Use an ordinal such as `get 2.kun` when duplicate items need an explicit selection.

NPC targets for `talk`, `consider`, `attack`, and `throw` accept name prefixes and ordinals such as `talk guard` or `consider 2.guard`, which keeps long builder-authored names usable from the command line.

### Social Consent

Socials now have authored catalog records instead of only free-form `emote` text. Normal socials are visible by default, while adult intimate and BDSM categories require explicit opt-in through `consent` before they appear in `socials` or can be used. Targeted socials that touch, pull, restrain, or otherwise affect another character check the target's consent before they resolve.

Mechanical social states are intentionally revocable. `holdhands` can lead a consenting character through ordinary movement. `tie` and `restrain` block movement only after explicit consent, and the target can always use `resist` or revoke consent. `release` clears states controlled by the acting character.

### Editable Help Files

Command summaries, longer help prose, and publish state live in `helpfiles/commands.json`. Builders and helpers can update each command's `summary`, `details`, and `published` state without editing Python or restarting the server. Both `commands` and `help <command>` read the file when requested. Unpublished help shows `(i)`.

Command-catalog sections live in `helpfiles/command_categories.json`. Builders can reorder commands or move them between headings such as `Movement`, `Builder`, and `Admin`. Section headings receive ANSI color when the player's color setting is enabled.

Use `hedit <command> summary <text>`, `hedit <command> detail <text>`, `hedit <command> category <section>`, `hedit <command> publish`, and `hedit <command> unpublish` to manage command help in-game.

Keep executable command syntax, aliases, permissions, and validation rules in Python. Missing entries or temporarily invalid JSON fall back to the built-in command summaries and an `Other` section so command discovery remains available while a help-file edit is repaired.

Admin access tools:

- `players`: list every registered account with online status, access flags, identity summary, saved location, and last-login timestamp.
- `finger <username>`: inspect a player's persistent identity, admin/builder access, online state, created and last-login timestamps, resources, attributes, body state, stance, saved location, skills, and jutsus without exposing password data.
- `pstat <username>`: compatibility alias for the detailed `finger` inspection.
- `pedit <username> builder on|off`: grant or remove builder access without granting full admin access.
- `pset <username> <field> <value>`: set a validated player field such as `admin`, `builder`, `specialty`, `clan`, `release`, `dojo`, description, resources, `intellect`, `condition`, other attributes, nutrition, hydration, or fatigue.
- `copyover`: report that soft restarts are intentionally disabled for now.

Builder overlay tools:

- `buildzone <zone_key> <start_vnum> <end_vnum> <x> <y> <room_title>`: create an anchored zone with one usable starting room and move there.
- `zonelist`: list authored zone filenames, ranges, anchors, and room counts.
- `zstat [zone]`: show compact zone counts for rooms, templates, spawns, range, and anchor.
- `rlist [zone]`, `mlist [zone]`, and `ilist [zone]`: list authored rooms, NPC templates, and item templates.
- `bfind <text>`: search authored rooms, NPC templates, item templates, spawns, keywords, names, and VNUMs.
- `contentcheck [zone]`: validate exits, VNUM references, spawn templates, duplicate VNUMs, overlapping coordinates, and out-of-bounds overlays.
- `zpublish [zone]`: validate a zone, mark it published, reload overlays, and record the publish in builder audit.
- `goto <vnum>`: teleport to an authored overlay room while retaining canonical coordinates.
- `goto grid <x> <y>`: teleport to canonical world coordinates.
- `goto player <name>`: teleport to an online character.
- `zoneinfo [vnum]`: inspect the current or requested overlay room.
- `placezone <zone_file> <x> <y>`: persist a zone anchor and reload overlays.
- `reloadcontent`: import authored JSON template changes and missing spawns into live state.
- `dig <direction> <room_name>`: create a coordinate-aware authored room and reciprocal exit.
- `roomdesc <description>`: replace the current authored room description.
- `redit <title|desc|flag|exit|link|unlink> <value>` and `rstat [vnum]`: edit and inspect room titles, descriptions, flags, explicit exits, reciprocal links, and unlinking.
- `rdelete <vnum>`: delete an authored room only after exits, incoming links, and authored spawns are cleared.
- `createnpc <npc_key> <name>`: create a basic static authored NPC template in the current zone.
- `medit <npc_key> <field> <value>` and `mstat <npc_key>`: edit and inspect NPC prose, behavior, PC-like resources and stats, combat bonuses, techniques, jutsus, respawn timing, loot table, room emote, movement policy, leash radius, and aggression policy.
- `spawnnpc <npc_key>`: persist and import an authored NPC spawn in the current room.
- `iedit create <item_key> <name>`, `iedit <item_key> <field> <value>`, and `istat <item_key>`: create, edit, and inspect authored item templates including type, slot, flags, value, weight, stack limit, container capacity, use text, damage, throw damage, nutrition, and hydration.
- `spawnitem <item_key>`: persist and import a finite authored item seed in the current room.
- `cloneitem <source_key> <new_key>`, `clonenpc <source_key> <new_key>`, and `cloneroom <source_vnum> <new_vnum>`: copy authored content for fast variations.
- `spawnlist [zone]`: list authored NPC and item spawns.
- `despawnitem <spawn_key>` and `despawnnpc <spawn_key>`: remove authored item or NPC spawns from the current zone.
- `zdelete <zone>`: delete an authored zone only after external links and authored spawns are cleared.
- `bundo`: restore the most recent successful builder zone mutation snapshot.
- `hedit <command> <summary|detail|category|publish|unpublish> [text]`: edit and publish command help.
For a fresh zone, start with `buildzone`, use `zstat`, `rlist`, `mlist`, `ilist`, `bfind`, and `contentcheck` to inspect it, use `dig` to expand its coordinate layout, use `redit` and `rstat` to refine rooms, then create templates with `createnpc` or `iedit` and place finite instances with `spawnnpc` or `spawnitem`. Use clone commands for variations, `spawnlist` plus despawn commands for authored seeds, `zpublish` before treating a zone as ready, and `bundo` to revert the most recent successful builder mutation. JSON remains the authored source of truth, while successful edits synchronize live SQLite template metadata immediately.

`pedit` and `pset` deliberately exclude usernames, passwords, and saved coordinates. Those need separate audited workflows; ordinary player movement and `goto` remain the safe ways to change location. The older `setrole`, `setstat`, and `setdojo` commands remain available as compatibility wrappers.

The player prompt reports current and maximum health, stamina, chakra, and location after commands. Map output includes a legend for you, other players, NPCs, and authored areas. Nearby-character listings are controlled by `show_nearby_players` and `nearby_player_radius` in `config.json`.

ANSI terminal colors are enabled for new connections by default. Set `default_color_enabled` in `config.json` to change the server default, or use `color off` for clients that do not render ANSI colors cleanly.

Room items, character inventories, equipped slots, and NPC instances persist in SQLite. Authored templates, item keywords, equipment metadata, and initial VNUM placements live in zone JSON files such as `zones/eveshaven.json`. Startup imports missing spawns once, so picked-up items are not recreated on every restart.

Eve's Haven authors a Haven Map, Travel Ration, and Water Flask at its entrance, a Practice Kunai in its garden, a Crystal Token in its library, a Haven Guide NPC at the entrance, and a hostile Practice Construct in the garden. `reloadcontent` lets an admin apply JSON template edits and create newly-authored spawns without restarting the server.

Eve's Haven is also the compact training loop. Pick up food and water at the entrance, move north into the garden for the Practice Kunai and Practice Construct, then exercise melee, `throw`, `usejutsu substitution`, `body`, and `rest`.

The combat loop is engagement-driven and round-based. `attack <character>` starts or retargets combat without dealing immediate damage. Basic auto attacks resolve on action rounds derived from Dexterity and Agility: `1 + 4 * average(dexterity, agility) / 100`, capped from `1` to `5` attacks per second. Engagement remains active when a player moves away, so repositioning creates space instead of acting as a separate flee command. Defeated NPCs disappear until their authored respawn delay elapses. A defeated player recovers to maximum health at the same grid coordinate.

NPCs now use the same core resource/stat shape as player characters: health, stamina, chakra, Strength, Dexterity, Agility, Intelligence, and Wisdom. Builder-created NPCs default those values to `10`. Legacy NPC `damage`, `accuracy`, and `evasion` fields remain as explicit combat bonuses, while authored `techniques` let NPCs spend stamina on the same combat techniques players can use.

`stance` adds the first authored combat profiles. The current placeholders keep neutral timing, so stance choice only changes combat tradeoffs:

- `S1 - Attack`: `+2` accuracy, `-1` damage, `-1` evasion.
- `S2 - Damage`: `+2` damage, `-1` accuracy, `-1` evasion.
- `S3 - Balance`: no modifiers.
- `S4 - Evasion`: `+2` evasion, `-1` accuracy, `-1` damage.
- `S5 - Damage Reduction`: `+2` incoming damage reduction, `-1` accuracy, `-1` damage.

Accuracy and evasion are opposing values. An S1 attacker facing an S2 defender has an easier hit check because the attacker contributes `+2` accuracy while the defender contributes `-1` evasion. NPC combat uses NPC Dexterity and Agility with optional authored accuracy/evasion bonuses. Player-versus-player engagement can reuse the opposed calculation when it is introduced. The persisted combat queue can still apply one-shot range, accuracy, damage, and status modifiers from future skills and jutsus.

`technique` adds stamina-based fighting techniques that queue one round modifier. Use `technique` to list available moves, `technique <name>` to queue one, or the direct command name for the first set. Queueing a new technique replaces the previous queued technique. Stamina is spent when queued, and out-of-range rounds keep the technique pending until an eligible round resolves.

- `strike`: costs `2` stamina and adds `+2` damage to the next round attack.
- `guard`: costs `2` stamina, skips your outgoing round attack, adds `+2` evasion, and reduces incoming damage by `2`.
- `feint`: costs `3` stamina, adds `+4` accuracy, and adds `+1` damage to the next round attack.
- `recover`: costs `0` stamina, skips your outgoing round attack, and restores up to `4` stamina on the next round.

Characters also have abstract body resources: nutrition, hydration, and fatigue. Ordinary movement and hostile combat increase fatigue. `rest` reduces fatigue, consumes a small amount of nutrition and hydration, restores stamina, and restores chakra based on intellect and current body condition. Condition improves short-rest recovery, and recovery-friendly rooms add a room bonus. Rest is blocked at zero nutrition or hydration. `eat` and `drink` consume finite authored supplies to restore body resources.

Room flags have player-visible effects. `darkness` hides survey and nearby maps, `brightness` washes the minimap, `indoor` limits map visibility, `safe` and `no-combat` block player combat commands, `vacuum` adds fatigue and can pressure health at extreme fatigue, and `recovery-friendly` improves rest.

Skills and jutsus have separate authored definitions and hidden point progress. `prac <skill>` and `train <jutsu>` add practice points and report visible tier progress without raw percentages, with milestone messages at meaningful improvements and tier changes. `skill` and `jutsu` list available records, and `skill all` plus `jutsu all` expose the wider authored catalog with future records marked `[unimplemented]`. Visible tiers are `Untrained`, `Unlearned`, `Novice`, `Adept`, `Trained`, `Master`, and capped `Grandmaster`.

`throw <item> at <character>` is the first real skill action. A valid throw accepts a carried authored item with ranged damage, targets a hostile NPC in the current room or one cardinal step away, adds `2` fatigue, lands the item at the target location, and raises `Throw` proficiency even when the attack misses. The Practice Kunai deals `3` thrown damage.

`usejutsu substitution` prepares Substitution Technique for `30` seconds at a cost of `3` chakra. The next eligible hostile NPC strike during that window is avoided, successful resolution raises Substitution proficiency, and the technique then remains on a persisted `60` second cooldown.

### Early Linux Testing

The current MUD socket uses plain-text TCP. Passwords are hashed safely in the database, but they are still sent over the network as plain text during login. Encrypted transport means wrapping that connection in TLS, or keeping it inside a trusted VPN, so someone watching network traffic cannot read login passwords.

For early Linux testing, restrict access with a firewall allowlist, private network, or VPN. Do not expose password login to the open internet until encrypted transport is added.
