# Changelog

## 2026-06-02 15:51 -0500 - Neutral Stance Profiles

### Added

- Added migration `15` for persisted stance damage reduction.
- Added five neutral placeholder profiles: S1 attack, S2 damage, S3 balance, S4 evasion, and S5 damage reduction.
- Displayed active stance in `score`, `combat`, and admin `pstat`.

### Changed

- Removed the temporary mongoose and crane profiles and cleared saved references to them during migration.
- Standardized placeholder stances on the same `6` second auto-attack pulse so stance selection only changes combat tradeoffs.
- Applied S5 damage reduction to incoming hostile NPC pulse damage.

### Verification

- Added authored-profile, S1 accuracy, S2 damage, S4 evasion, S5 reduction, inspection-output, and migration cleanup regression coverage.
- Upgraded the preserved local database through migration `15` while retaining its `7` player rows.
- Passed `python -m unittest discover -s tests -v` with `166` tests.
- Passed Python syntax compilation, JSON validation, and `git diff --check`.

## 2026-06-02 15:36 -0500 - Fluid Pulse Combat Foundation

### Added

- Added migration `14` for persisted combat engagements, authored character stances, and one-shot queued combat modifiers.
- Added `combat` for inspecting live engagement range and `stance` for listing or switching authored stances.
- Added Mongoose Stance and Crane Stance with deliberately different accuracy, evasion, and pulse-speed tradeoffs.

### Changed

- Changed `attack <character>` from an immediate exchange into engagement entry or retargeting.
- Kept basic auto attacks up close while allowing engagement to remain active across movement, avoiding a separate flee command.
- Added a dedicated scheduler check for due combat pulses while keeping slow per-character attack timing.

### Verification

- Added pulse engagement, movement-range, queued-range, authored-stance, substitution, scheduler-delivery, and migration regression coverage.
- Upgraded the preserved local database through migration `14` while retaining its `7` player rows.
- Passed `python -m unittest discover -s tests -v` with `160` tests.
- Passed Python syntax compilation, JSON validation, and `git diff --check`.
- Passed an isolated temporary-database TCP smoke for stance selection, engagement entry, pulse delivery, and movement spacing.

## 2026-06-02 15:21 -0500 - Player Administration and Builder Roadmap

### Added

- Added `pstat <username>` for password-safe inspection of persistent player identity, access, resources, body state, and saved location.
- Added `pset <username> <field> <value>` for validated player administration across access, identity, resources, attributes, nutrition, hydration, and fatigue.
- Added a prioritized builder-suite roadmap covering search, validation, cloning, spawn management, guarded deletion, undo, richer templates, and audit history.

### Changed

- Kept `setrole`, `setstat`, and `setdojo` as compatibility wrappers around the validated `pset` path.
- Refresh connected protocol metadata immediately when `pset` changes admin access or specialty.
- Clamp current health, stamina, or chakra when an administrator lowers the corresponding maximum.

### Verification

- Passed `python -m unittest discover -s tests -v` with 151 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 15:08 -0500 - Sprint 18 Builder Editing Suite

### Added

- Added `buildzone` and `zonelist` for a clear in-game path from empty grid to anchored authored zone.
- Added `redit` and `rstat` for room titles, descriptions, flags, exits, offsets, and inspection.
- Added `medit` and `mstat` for authored NPC prose, behavior, combat values, respawn timing, and inspection.
- Added `iedit`, `istat`, and `spawnitem` for authored item creation, editing, inspection, and finite persistent placement.

### Changed

- Display authored room titles in normal room rendering while retaining zone names as the fallback for existing content.
- Reject accidental blank builder prose before JSON persistence.
- Marked Sprint 18 complete and moved the active roadmap to private-alpha exercise.

### Verification

- Passed `python -m unittest discover -s tests -v` with 147 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 14:57 -0500 - Categorized Command Catalog

### Added

- Added `helpfiles/command_categories.json` so builders and helpers can reorganize command-catalog sections without editing Python.
- Added clean catalog headings such as `Movement`, `Builder`, and `Admin`, with ANSI color when the player's color setting is enabled.
- Tracked the authored `aexpanse` overlay with its two rooms and seeded Living Void NPC.

### Changed

- Added an `Other` fallback section so missing or temporarily invalid category JSON never hides registered commands.
- Updated startup and authored-content coverage to support multiple anchored overlay zones while restoring global runtime configuration between tests.
- Reorganized the active roadmap so the expanded builder editing suite is Sprint 18 and the private-alpha soak pass follows as Sprint 19.

### Verification

- Passed `python -m unittest discover -s tests -v` with 143 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 11:14 -0500 - Builder-Editable Help Files

### Added

- Added `helpfiles/commands.json` with editable summaries and detailed help prose for every registered command.
- Added request-time help loading so builders and helpers can refresh prose without editing Python or restarting the server.

### Changed

- Kept executable usage syntax, aliases, permissions, handlers, and validation rules in Python.
- Added safe fallback to built-in command summaries when an editable help entry is missing or the JSON file is temporarily invalid.

### Verification

- Added editable-catalog completeness, request-time refresh, and malformed-file fallback coverage.
- Passed `python -m unittest discover -s tests -v` with 140 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 11:09 -0500 - Complete Command Catalog

### Added

- Added `commands` to list every registered player and admin command with usage and a brief description.
- Marked admin-only entries and displayed aliases directly in the generated catalog.
- Kept `help <command>` as the detailed lookup for individual commands.

### Verification

- Added catalog content and registry-completeness coverage.
- Passed `python -m unittest discover -s tests -v` with 137 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 11:05 -0500 - Coordinate Overlay Builder

### Added

- Added `dig <direction> <room_name>` for persisted coordinate-aware rooms with reciprocal exits.
- Added `roomdesc <description>` for authored overlay room editing.
- Added `createnpc <npc_key> <name>` and `spawnnpc <npc_key>` for basic static NPC templates and persistent seeded spawns.
- Documented Eve's Haven entrance and garden as a compact training path for recovery, melee, Throw, and Substitution Technique.

### Changed

- Reloaded and validated live overlays after builder edits, rolling JSON back when an edit would leave invalid authored coordinates.

### Verification

- Added room-digging, coordinate-collision, description-persistence, NPC-template, spawn-seed, and reload-deduplication coverage.
- Passed `python -m unittest discover -s tests -v` with 135 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 10:59 -0500 - Substitution Technique Vertical Slice

### Added

- Added authored jutsu execution metadata and persisted per-character activation state through migration 13.
- Added `usejutsu <jutsu>` and implemented Substitution Technique as a `3` chakra preparation with a `30` second defensive window and a `60` second cooldown.
- Added scheduler cleanup for expired jutsu activations and cooldowns.

### Changed

- Made the next eligible hostile NPC strike consume prepared Substitution Technique instead of damaging the player.
- Raised Substitution proficiency when its defensive effect resolves successfully.

### Verification

- Added activation, insufficient-chakra, persistence, expiry, defensive-resolution, cooldown, and transactional rollback coverage.
- Passed `python -m unittest discover -s tests -v` with 132 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 10:40 -0500 - Roadmap and Changelog Consolidation

### Changed

- Reorganized `TODO.md` into a concise active roadmap with completed checkpoints summarized once.
- Made Substitution Technique the single active Sprint 16 implementation queue.
- Added timestamps to roadmap-era changelog headings using corresponding Git commit times.

## 2026-06-02 10:33 -0500 - Throw Skill Vertical Slice

### Added

- Added `throw <item> at <character>` for hostile NPCs in the current room or one cardinal step away.
- Added authored `throw_damage` through migration 12; Practice Kunai deals 3 ranged damage.
- Added transactional ranged item handling: valid throws add 2 fatigue, land the item at the target location, and raise `Throw` proficiency on hits or misses.

### Verification

- Added ranged hit, miss, adjacency, non-throwable rejection, migration, and rollback coverage.
- Passed `python -m unittest discover -s tests -v` with 127 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 10:19 -0500 - Usage-Based Skill and Jutsu Framework

### Added

- Added separate authored skill and jutsu definitions with persistent per-character proficiency through migrations 9 and 10.
- Added `prac [skill]` and `train [jutsu]` for listing ordinary skills and jutsus or inspecting proficiency.
- Seeded `Throw` and `Substitution Technique` as the first framework records.
- Added reusable valid-use progression helpers with authored gains, a `100%` cap, and `Novice` through `Grandmaster` display tiers.
- Added `skill [all|skill]` and `jutsu [all|jutsu]` discovery commands.
- Added catalog-only placeholder skills and jutsus through migration 11; placeholders are marked `[unimplemented]` and cannot gain proficiency.

### Changed

- Replaced point-spend advancement with usage-based proficiency.
- Deferred ranged attacks, chakra costs, cooldowns, cast timing, and Substitution combat effects to the first technique vertical slice.

### Verification

- Added authored-sync, valid-use advancement, cap, invalid-target, tier-boundary, migration, and reconnect-persistence coverage.
- Passed `python -m unittest discover -s tests -v` with 121 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 09:46 -0500 - Body Resource Integration

### Added

- Added authored Travel Ration and Water Flask consumables through migration 8 item metadata.
- Added `eat <item>` and `drink <item>` with existing item keyword, prefix, and ordinal targeting.
- Added body warnings for low nutrition, low hydration, and strained fatigue.

### Changed

- Blocked short rests when nutrition or hydration reaches zero.
- Kept authored consumables finite: consumed seeded items remain absent after content reload.

### Verification

- Added migration, consumable, targeting, depletion, warning, and content-reload regression coverage.
- Passed `python -m unittest discover -s tests -v` with 112 tests.
- Passed Python syntax compilation and `git diff --check`.

## 2026-06-02 09:42 -0500 - Body and Social Foundation

### Added

- Added persistent abstract nutrition, hydration, fatigue, and recovery-readiness fields through migration 7.
- Added `body` for condition inspection and `rest` for deliberate stamina and chakra recovery.
- Added private online `whisper` messages and nearby `shout` messages for the current and adjacent grid coordinates.

### Changed

- Increased fatigue through ordinary movement and valid hostile combat turns.
- Made short-rest chakra recovery depend on wisdom, nutrition, hydration, and fatigue.
- Extended terminal-control sanitization to whispers and shouts.
- Deferred reproductive and mature-consequence mechanics until an explicit adult-only opt-in roleplay design exists.

### Verification

- Added body migration, recovery, exertion, whisper, shout, and sanitization coverage.
- Passed `python -m unittest discover -s tests -v` with 105 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-02 09:42 -0500 - Runtime State Ownership

### Changed

- Removed SQLite database creation from module import side effects.
- Kept one server-maintenance SQLite connection for initialization, validation, authored-content synchronization, and scheduled world ticks.
- Changed live protocols to receive independent factory-created SQLite connections and close them on disconnect.
- Prevented pre-login disconnects from broadcasting departure messages for sessions that never joined a tracked room.

### Verification

- Added lifecycle coverage for independent factory sessions, owned-connection cleanup, pre-login disconnects, player commands, repeated initialization, and world ticks after session disconnects.
- Passed `python -m unittest discover -s tests -v` with 97 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-02 09:42 -0500 - ANSI Presentation QoL

### Added

- Added semantic ANSI styling for prompts, room titles, room-section labels, map markers, and social-channel metadata.
- Added `color on|off` for changing ANSI output during the current connection.
- Added `default_color_enabled` configuration, enabled by default.

### Changed

- Removed terminal control sequences from player-authored `say`, `ooc`, and `emote` text before broadcasting it.
- Kept plain-text rendering intact for clients with color disabled.

### Verification

- Added presentation coverage for toggling, colored prompts, colored maps, plain output, and chat sanitization.
- Passed `python -m unittest discover -s tests -v` with 92 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 17:30 -0500 - Combat Reliability

### Added

- Added bounded hit chances using player dexterity versus NPC evasion and NPC accuracy versus player agility.
- Added authored NPC accuracy and evasion metadata with migration 6 for existing databases.
- Added `consider <character>` for inspecting visible NPC health and combat stats.
- Added room broadcasts for attacks, misses, damage, and defeats.

### Changed

- Applied equipped item damage bonuses to basic melee attacks without hardcoding Practice Kunai behavior.
- Wrapped shared NPC combat turns in SQLite write transactions so failed turns roll back cleanly.
- Defined player defeat recovery as full health at the same grid coordinate.

### Verification

- Added coverage for misses, weapon bonuses, combat inspection, room broadcasts, shared-NPC multiplayer damage, rollback behavior, and legacy NPC schema upgrades.
- Upgraded the preserved local development database through migration 6.
- Passed `python -m unittest discover -s tests -v` with 86 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 15:50 -0500 - Inventory Management and Character Foundation

### Added

- Added authored item keywords, item types, equipment slots, usage text, and future-facing damage bonuses.
- Added abbreviated and ordinal item targeting, including commands such as `get kun` and `get 2.kun`.
- Added `examine`, `look at`, `wield`, and `remove`, with persistent equipped slots and clearer inventory formatting.
- Added durable maximum health, stamina, and chakra fields alongside clan and natural release.

### Changed

- Replaced incremental character stats with one named allocation line whose bonuses total exactly 10.
- Added specialty, clan, and natural-release choices to new-character creation and displayed them in `score`.
- Made routine room views compact while keeping the larger terrain map under `survey`.
- Grouped room details into readable blocks and removed noisy empty-room lines.
- Recovered defeated players to their stored maximum health.

### Verification

- Added migration coverage for existing private-alpha characters and interaction coverage for abbreviated targets, duplicate items, examination, and persistent equipment.
- Upgraded the preserved local development database through migration 5 while retaining its existing player rows.
- Passed `python -m unittest discover -s tests -v` with 79 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 15:39 -0500 - Inventory Sprint Reprioritization

### Changed

- Moved inventory management and room presentation ahead of combat reliability as Sprint 12.
- Planned authored item keywords, abbreviated item targeting, ordinal duplicate selection, examination, equipment persistence, and wielding.
- Defined the Practice Kunai as the first authored weapon/tool while deferring thrown attacks until ranged combat rules are deliberate.
- Added a presentation cleanup pass for compact maps and readable room sections.
- Shifted combat reliability, character foundation, chakra abilities, builder tooling, and the private-alpha exercise to Sprints 13 through 17.

## 2026-06-01 15:34 -0500 - Post-Combat Roadmap Checkpoint

### Changed

- Reconciled the active roadmap after the basic NPC combat slice.
- Adopted milestone sprints with one testable vertical slice, regression coverage, smoke-test notes, documentation, changelog updates, and a focused commit per sprint.
- Ordered the next work as combat reliability, character foundation, first chakra ability, builder tools and training content, then a private Linux exercise.
- Clarified that `TODO.md` is the active implementation queue while documents under `Content/` remain long-term design references.

### Verification

- Passed `python -m unittest discover -s tests -v` with 74 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 15:19 -0500 - Basic NPC Combat Slice

### Added

- Added `attack <character>` with strength-based player damage and immediate hostile NPC counterattacks.
- Added authored NPC combat tuning, persistent live health, defeat timestamps, and scheduler-driven respawns.
- Added the hostile Practice Construct to Eve's Haven garden as the first combat target.

### Changed

- Chose a command-driven turn model for the first combat loop: one player strike followed by one surviving hostile counterattack.
- Made defeated NPCs disappear from room listings and dialogue until recovery.
- Recover defeated players immediately to 10 health while retaining persistent combat state.

### Verification

- Added combat coverage for damage, counterattacks, protected and missing targets, NPC defeat and respawn, player recovery, and reconnect persistence.
- Upgraded the preserved local development database through migration 4 while retaining its seven player rows.
- Passed `python -m unittest discover -s tests -v` with 74 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 15:13 -0500 - JSON-Authored Content and NPC Foundation

### Added

- Added JSON-authored item templates and VNUM-based initial placements for Eve's Haven.
- Added persistent NPC templates and spawned NPC instances with a recurring lightweight world tick.
- Added the Haven Guide NPC, room visibility, and `talk <character>` dialogue.
- Added `reloadcontent` for importing authored JSON template edits and missing spawns while the server is running.

### Changed

- Renamed the configured local SQLite database from `mud_game_10_rooms.db` to `shinobi_mud.db`.
- Preserved authored item provenance so content reloads do not recreate objects after players pick them up.

### Verification

- Upgraded the preserved local development database through migration 3 while retaining its seven player rows.
- Added NPC coverage for authored imports, visibility, dialogue, admin reloads, and recurring world ticks.
- Passed `python -m unittest discover -s tests -v` with 69 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 15:01 -0500 - Persistent Items and Inventories

### Added

- Added versioned SQLite storage for item definitions, coordinate-based room items, and character inventories.
- Seeded a Haven Map, Practice Kunai, and Crystal Token into Eve's Haven on fresh database migration.
- Added `inventory`, `get <item>`, and `drop <item>` player commands.
- Displayed visible persistent items in room descriptions on authored overlays and open wilderness.

### Verification

- Added item-slice coverage for idempotent migration seeding, room visibility, pickup/drop transfers, reconnect persistence, and invalid operations.
- Passed `python -m unittest discover -s tests -v` with 63 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 14:54 -0500 - Private Alpha Hardening and Player Feedback

### Added

- Added a basic Linux private-alpha checklist with an optional `systemd` service.
- Logged unexpected reactor failures in the existing timestamped launch log.
- Added compact player prompts, map legends, location-aware `score` output, and configurable nearby-character listings.
- Added `goto grid <x> <y>` and `goto player <name>` admin travel while retaining `goto <vnum>`.

### Changed

- Disabled unfinished `copyover` behavior with an explicit admin-facing status response.
- Documented the plain-text TCP limitation and the trusted-network requirement for private tests.

### Verification

- Added regression coverage for crash logging, disabled copyover, prompts, nearby-character listings, map legends, and admin grid/player teleports.
- Passed `python -m unittest discover -s tests -v` with 58 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 14:47 -0500 - Post-Foundation Roadmap Checkpoint

### Added

- Added timestamped per-launch runtime logs under `logs/`.
- Reconciled `TODO.md` against the completed foundation and ordered the post-foundation roadmap.

### Changed

- Ignored local launch logs and generated copyover state in Git.
- Updated the README to describe the implemented private-alpha feature set accurately.

### Verification

- Added startup coverage for nested runtime-log directory creation.
- Passed `python -m unittest discover -s tests -v` with 51 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 12:09 -0500 - First Overlay Content Slice

### Added

- Anchored Eve's Haven at `(500, 500)` with 30 distinct VNUM-backed room overlays.
- Loaded anchored zone overlays during startup without mutating wilderness terrain.
- Displayed authored zone names, VNUMs, descriptions, and exits when players enter or inspect overlay rooms.
- Added `goto <vnum>`, `zoneinfo [vnum]`, and `placezone <zone_file> <x> <y>` admin tools.

### Changed

- Kept `(x, y)` coordinates canonical for wilderness movement, overlay movement, admin teleports, chat, persistence, and reconnects.
- Made overlay reload atomic and rolled back failed zone placements.

### Verification

- Added vertical-slice tests for loading, entry, exit, local chat, reconnects, VNUM lookup, admin inspection, teleports, persisted anchors, and failed-placement rollback.
- Passed `python -m unittest discover -s tests -v` with 50 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 12:03 -0500 - Command Prefix Matching

### Added

- Added automatic unique-prefix matching for registered commands.
- Reserved `n`, `s`, `e`, `w`, and `l` as stable shortcuts for movement and `look`.
- Added clear ambiguity responses when a prefix matches more than one command.
- Added metadata-driven command registration with usage, descriptions, semantic aliases, and permission levels.
- Added `help` and `help <command>` output generated from command metadata.

### Changed

- Routed admin authorization through command permission metadata.
- Centralized argument-count validation and useful usage responses.
- Normalized command parsing across spaces, tabs, and surrounding whitespace.
- Kept `status` as an explicit semantic alias for `score`.

### Verification

- Added command-layer tests for metadata, permissions, usage errors, help visibility, semantic aliases, whitespace parsing, prefixes, stable shortcuts, ambiguity, and unknown commands.
- Passed `python -m unittest discover -s tests -v` with 43 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 10:56 -0500 - Movement Lock Recovery

### Fixed

- Limited SQLite lock waits so a blocked location save does not stall every connected player.
- Made movement persistence atomic: players remain at their original location when a coordinate update cannot be saved.
- Added a clear retry message when movement persistence is temporarily blocked.
- Listed other characters already present after entering a location by movement or login.

### Verification

- Added regression coverage for blocked movement saves and the player-facing retry response.
- Passed `python -m unittest discover -s tests -v` with 30 tests.
- Passed Python syntax compilation and a file-backed SQLite lock probe.

## 2026-06-01 10:45 -0500 - Multiplayer Basics

### Added

- Added `who` to list connected characters.
- Added `score` for a clearer character sheet while keeping `status` as an alias.
- Added `loc` to report grid coordinates and optional overlay metadata.
- Added arrival, departure, and movement notices for characters sharing a location.
- Added multiplayer tests for local chat, global OOC, simultaneous players, movement notices, disconnect cleanup, `who`, `score`, and `loc`.

### Changed

- Fixed `say`, `emote`, and `think` as coordinate-local commands.
- Confirmed `ooc` as a global channel delivered once to each connected character.
- Removed command arguments and conversation text from routine server logs.
- Centralized online-player lookup and location broadcasting.

### Verification

- Passed `python -m unittest discover -s tests -v` with 26 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 10:39 -0500 - Coordinate-First World Locations

### Added

- Added a coordinate-first location API for bounds checks, cardinal destinations, player tracking, movement, persistence, and optional authored overlays.
- Added a world-overlay registry keyed by `(x, y)` coordinates.
- Added location tests for movement persistence, reconnects, tracking buckets, boundaries, overlay lookup, and map rendering.

### Changed

- Made `(x, y)` coordinates the only canonical player location.
- Updated movement to move players between tracking buckets and save coordinates immediately.
- Updated nearby-player lookup and local social commands to use coordinate keys.
- Fixed `survey` rendering and made map radius configurable.
- Changed zone overlays to attach metadata without mutating terrain cells.
- Disabled legacy VNUM `goto` and `dig` until coordinate-aware builder tools are introduced.
- Updated copyover state to store coordinates.

### Verification

- Passed `python -m unittest discover -s tests -v` with 18 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 10:29 -0500 - Test Harness and Runtime Baseline

### Added

- Added a standard-library `unittest` suite for account lifecycle, permissions, and startup behavior.
- Added a startup smoke test using an isolated temporary SQLite database and a fake reactor.
- Added startup validation for configuration, database tables, utilities, command registration, world-map data, and the configured zone directory.
- Documented the local reset, test, and run workflow.

### Changed

- Loaded the TCP listening port from `config.json` instead of hardcoding `4000`.
- Split server initialization from reactor startup so runtime behavior can be smoke-tested without opening a real socket.
- Reused the active `shinobi_mud` module when launched as a script so command imports do not create a second copy of global server state.
- Made repeated logging initialization close and replace existing handlers cleanly.

### Verification

- Passed `python -m unittest discover -s tests -v` with 11 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 10:25 -0500 - Foundation and Account Security Checkpoint

### Added

- Added `FOUNDATION_CHECKLIST.md` with an ordered roadmap and live-testing gates.
- Added `requirements.txt` for Python dependencies.
- Added a disposable local database reset workflow with archived backups.
- Added versioned SQLite migrations.
- Added a local CLI for intentionally promoting an existing account to admin.
- Added salted `scrypt` password hashing with transparent legacy SHA-256 upgrades.
- Added username validation and duplicate-session protection.

### Changed

- Redacted password and password-confirmation input from logs.
- Made new accounts non-admin by default.
- Added authorization checks around all admin commands.
- Replaced fragile numeric login indexes with named SQLite row fields.
- Corrected loading of saved coordinates, admin status, and role data during login.
- Rejected zero, negative, and over-budget stat allocations.
- Updated setup documentation for Windows and Linux testing.
- Repaired the command module template so the repository compiles cleanly.

### Repository Hygiene

- Removed generated bytecode, runtime logs, the local SQLite database, IDE metadata, and local shortcuts from Git tracking.
- Expanded `.gitignore` so local runtime state stays out of future commits.

### Verification

- Verified Python syntax compilation.
- Verified password hashing, password checks, and legacy password upgrades.
- Verified migrations preserve existing admin accounts while defaulting new accounts to non-admin.
- Verified the admin-promotion CLI against a temporary database.
- Simulated registration, reconnect, duplicate-login denial, stat validation, and blocked non-admin `shutdown`.
- Manually verified the registration and reconnect flow through a running server.
