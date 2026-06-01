# Changelog

## 2026-06-01 - Combat Reliability

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

## 2026-06-01 - Inventory Management and Character Foundation

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

## 2026-06-01 - Inventory Sprint Reprioritization

### Changed

- Moved inventory management and room presentation ahead of combat reliability as Sprint 12.
- Planned authored item keywords, abbreviated item targeting, ordinal duplicate selection, examination, equipment persistence, and wielding.
- Defined the Practice Kunai as the first authored weapon/tool while deferring thrown attacks until ranged combat rules are deliberate.
- Added a presentation cleanup pass for compact maps and readable room sections.
- Shifted combat reliability, character foundation, chakra abilities, builder tooling, and the private-alpha exercise to Sprints 13 through 17.

## 2026-06-01 - Post-Combat Roadmap Checkpoint

### Changed

- Reconciled the active roadmap after the basic NPC combat slice.
- Adopted milestone sprints with one testable vertical slice, regression coverage, smoke-test notes, documentation, changelog updates, and a focused commit per sprint.
- Ordered the next work as combat reliability, character foundation, first chakra ability, builder tools and training content, then a private Linux exercise.
- Clarified that `TODO.md` is the active implementation queue while documents under `Content/` remain long-term design references.

### Verification

- Passed `python -m unittest discover -s tests -v` with 74 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 - Basic NPC Combat Slice

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

## 2026-06-01 - JSON-Authored Content and NPC Foundation

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

## 2026-06-01 - Persistent Items and Inventories

### Added

- Added versioned SQLite storage for item definitions, coordinate-based room items, and character inventories.
- Seeded a Haven Map, Practice Kunai, and Crystal Token into Eve's Haven on fresh database migration.
- Added `inventory`, `get <item>`, and `drop <item>` player commands.
- Displayed visible persistent items in room descriptions on authored overlays and open wilderness.

### Verification

- Added item-slice coverage for idempotent migration seeding, room visibility, pickup/drop transfers, reconnect persistence, and invalid operations.
- Passed `python -m unittest discover -s tests -v` with 63 tests.
- Passed Python syntax compilation across the repository.

## 2026-06-01 - Private Alpha Hardening and Player Feedback

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

## 2026-06-01 - Post-Foundation Roadmap Checkpoint

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

## 2026-06-01 - First Overlay Content Slice

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

## 2026-06-01 - Command Prefix Matching

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

## 2026-06-01 - Movement Lock Recovery

### Fixed

- Limited SQLite lock waits so a blocked location save does not stall every connected player.
- Made movement persistence atomic: players remain at their original location when a coordinate update cannot be saved.
- Added a clear retry message when movement persistence is temporarily blocked.
- Listed other characters already present after entering a location by movement or login.

### Verification

- Added regression coverage for blocked movement saves and the player-facing retry response.
- Passed `python -m unittest discover -s tests -v` with 30 tests.
- Passed Python syntax compilation and a file-backed SQLite lock probe.

## 2026-06-01 - Multiplayer Basics

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

## 2026-06-01 - Coordinate-First World Locations

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

## 2026-06-01 - Test Harness and Runtime Baseline

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

## 2026-06-01 - Foundation and Account Security Checkpoint

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
