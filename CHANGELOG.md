# Changelog

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
