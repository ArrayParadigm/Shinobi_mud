# Shinobi MUD Foundation Checklist

## Goal

Reach a stable starting point before expanding mapping, VNUM overlays, combat, or other large systems.

The immediate milestone is:

> Two non-admin accounts can register, log in, walk around, speak locally, disconnect, and return safely.

Work through each phase in order. Within a phase, complete tasks from top to bottom unless a task reveals a dependency that needs to move earlier.

---

## Live-Testing Gates

- **After Phase 1:** suitable for local account testing.
- **After Phase 2:** suitable for private Linux server smoke testing through a firewall allowlist, private network, or VPN.
- **After Phase 4:** suitable for a small private multiplayer alpha.
- **Before open-internet testing:** add encrypted transport so passwords are not sent over plain-text TCP.

---

## Phase 0: Repository Hygiene

- [x] 0.1 Add `requirements.txt` with `Twisted`.
- [x] 0.2 Stop tracking `mud_debug.log`, the live SQLite database, `__pycache__`, IDE metadata, and shortcuts.
- [x] 0.3 Expand `.gitignore`.
- [x] 0.4 Fix or remove the broken `command_template.py`.
- [x] 0.5 Add a disposable development database workflow.

### Done When

The repository can be cloned and set up without committing runtime state, secrets, or generated files.

---

## Phase 1: Secure Account Lifecycle

Fix the urgent account and authorization risks before expanding gameplay.

- [x] 1.1 Stop logging passwords and password confirmations.
- [x] 1.2 Add a migration system for controlled schema updates.
- [x] 1.3 Make new accounts non-admin by default in both the database and protocol state.
- [x] 1.4 Add a minimal authorization gate for every admin command.
- [x] 1.5 Add an intentional local workflow for promoting the first admin.
- [x] 1.6 Replace fragile numeric database indexes with named player fields during login.
- [x] 1.7 Correctly load saved coordinates, admin status, and role data on login.
- [x] 1.8 Replace raw SHA-256 password hashing with a salted password-hashing library.
- [x] 1.9 Temporarily support existing SHA-256 hashes and upgrade them after a successful login.
- [x] 1.10 Validate usernames: reject empty, invalid, and unreasonably long names.
- [x] 1.11 Prevent duplicate active sessions for the same username.
- [x] 1.12 Reject zero, negative, and over-budget stat allocations.
- [x] 1.13 Verify registration, stat allocation, disconnect, and reconnect manually.

### Done When

A new non-admin player can register, allocate stats, disconnect, reconnect, and recover the same character safely. Existing accounts can still log in and are upgraded to the new password format.

---

## Phase 2: Test Harness and Runtime Baseline

Add a safety net before refactoring shared gameplay state.

- [x] 2.1 Add a lightweight automated test setup.
- [x] 2.2 Add account tests for registration, login, legacy password upgrades, username validation, duplicate sessions, and stat allocation.
- [x] 2.3 Add permission tests proving non-admin players cannot run admin commands.
- [x] 2.4 Add a startup smoke test.
- [x] 2.5 Load the configured server port instead of hardcoding `4000`.
- [x] 2.6 Add startup validation for configuration, database setup, utilities, and command registration.
- [x] 2.7 Document a clean local setup, reset, run, and test workflow.

### Done When

Authentication and startup behavior can be checked quickly without manually connecting to the server for every change.

---

## Phase 3: One Location Model

Use `(x, y)` coordinates as the canonical player location. VNUM-backed zones can later be dropped onto the grid as optional content overlays.

- [ ] 3.1 Define a small location API for coordinate keys, lookups, and player movement.
- [ ] 3.2 Make `(x, y)` the only canonical player location.
- [ ] 3.3 Remove active gameplay dependencies on `current_room`.
- [ ] 3.4 Use the same coordinate key for player tracking and nearby-player lookups.
- [ ] 3.5 Move players between tracking buckets when coordinates change.
- [ ] 3.6 Save coordinates after movement.
- [ ] 3.7 Fix movement boundary handling.
- [ ] 3.8 Fix `look`, `survey`, and nearby-player listings.
- [ ] 3.9 Add automated tests for boundaries, tracking, lookups, and reconnect location persistence.

### Done When

Players can move, inspect their surroundings, disconnect, and return to the same grid position without location state drifting out of sync.

---

## Phase 4: Multiplayer Basics

- [ ] 4.1 Update local social commands to use coordinate-based player tracking.
- [ ] 4.2 Fix `say`, `emote`, and `think`.
- [ ] 4.3 Verify `ooc` as a deliberate global channel.
- [ ] 4.4 Add arrival and departure messages.
- [ ] 4.5 Add a `who` command.
- [ ] 4.6 Handle clean disconnects and tracking cleanup.
- [ ] 4.7 Add sensible command and error logging without leaking secrets.
- [ ] 4.8 Add automated tests for local chat range, global chat, disconnect cleanup, and simultaneous players.

### Done When

Two players can walk around, see one another, speak locally, use the global channel, disconnect cleanly, and return safely.

---

## Phase 5: Command Foundation

Build a consistent command layer after the core gameplay loop is reliable.

- [ ] 5.1 Separate command metadata from handlers: name, usage, permission level, and aliases.
- [ ] 5.2 Route the Phase 1 admin gate through command permission metadata.
- [ ] 5.3 Normalize argument handling.
- [ ] 5.4 Return useful usage messages instead of generic errors.
- [ ] 5.5 Add basic aliases: `n`, `s`, `e`, `w`, and `l`.
- [ ] 5.6 Add a `help` command driven by command metadata.
- [ ] 5.7 Add automated tests for aliases, usage errors, help output, and permissions.

### Done When

Commands are predictable, discoverable, and permission-aware without each module inventing its own rules.

---

## Phase 6: First Content Slice

Begin this phase only after the foundation is stable.

- [ ] 6.1 Define a grid-overlay lookup that can attach optional zone data to coordinates.
- [ ] 6.2 Keep coordinates canonical while exposing optional VNUM and room metadata.
- [ ] 6.3 Drop one small VNUM-backed zone onto the grid.
- [ ] 6.4 Add room descriptions and a few points of interest.
- [ ] 6.5 Add or repair admin tools needed to inspect and place the sample zone.
- [ ] 6.6 Validate entry, exit, movement, chat, reconnects, and admin building tools.
- [ ] 6.7 Add automated tests for overlay lookup and entering or leaving the sample zone.

### Done When

Eve's Haven is a small complete example proving that authored VNUM-backed content can be dropped onto the grid without creating a second competing location system.

---

## Later

Combat comes after the first content slice proves the foundation. Inventory, NPCs, richer prompts, world ticks, and expanded builder tools should be prioritized after the same core loop remains reliable with zone overlays enabled.
