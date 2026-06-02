# Shinobi MUD Active Roadmap

## Current Checkpoint

The private-alpha gameplay loop is covered by `160` automated tests. The current build includes:

- Coordinate-first wilderness movement with Eve's Haven as a VNUM-backed overlay zone.
- Persistent accounts, items, inventories, equipment, NPC instances, combat state, and body resources.
- Independent SQLite connections for server maintenance and connected player sessions.
- ANSI presentation, social commands, food and drink consumption, and deliberate recovery.
- Authored skill and jutsu catalogs with usage-based `0-100%` proficiency.
- `skill`, `prac`, `jutsu`, and `train` discovery commands with `[unimplemented]` catalog placeholders.
- A real `throw <item> at <character>` action. Practice Kunai throws deal `3` damage, add `2` fatigue, land at the target location, and raise `Throw` proficiency on valid hits or misses.
- A real `usejutsu substitution` action. It spends `3` chakra, prepares a `30` second defensive window, avoids the next eligible hostile NPC strike, raises Substitution proficiency on resolution, and persists a `60` second cooldown.
- Coordinate-aware builder commands for digging rooms, editing descriptions, creating basic NPC templates, and seeding persistent NPC spawns.
- Engaged in-game builder editing for anchored zones, rooms, NPC templates, item templates, and finite authored spawns.
- Consolidated `pstat` and validated `pset` player administration with compatibility wrappers for older setters.
- A complete `commands` catalog generated from registered help metadata.
- Builder-editable command summaries and detailed help prose loaded from `helpfiles/commands.json`.
- Builder-editable command-catalog sections with clean ANSI-colored headings loaded from `helpfiles/command_categories.json`.
- Persisted pulse combat engagements that remain active across movement, with up-close basic auto attacks and no separate flee command.
- Authored `Mongoose Stance` and `Crane Stance`, plus a queued-modifier foundation for later range, accuracy, damage, and status effects.
- `combat` and `stance` commands for inspecting and adjusting the live engagement loop.

The next step is exercising the expanded gameplay and builder loops through a private-alpha soak pass.

## Working Rules

Use this file as the active ordered implementation queue. Keep detailed history in `CHANGELOG.md` and larger design references under `Content/`.

Each sprint should end with:

- Automated regression tests.
- A manual smoke-test path.
- README updates for player or admin behavior.
- A timestamped changelog entry.
- A focused Git commit.

Only keep one sprint active at a time. Reassess the order after each committed slice.

## Completed Checkpoints

- [x] Account lifecycle, permissions, password hashing, and migrations.
- [x] Coordinate-first movement, overlays, player feedback, and multiplayer basics.
- [x] Persistent inventories, equipment, authored NPCs, melee combat, and combat reliability.
- [x] Character foundation, ANSI presentation, runtime database ownership, and body resources.
- [x] Food and drink consumption with recovery consequences.
- [x] Usage-based skill and jutsu framework with discoverable placeholder catalogs.
- [x] First real skill action: `Throw`.
- [x] First real jutsu action: `Substitution Technique`.
- [x] Coordinate-overlay builder and compact training playground.
- [x] Builder-editable help prose and categorized command discovery.
- [x] Sprint 18 builder editing suite.
- [x] Player inspection and validated player-setting administration.
- [x] Pulse combat engagements, authored stances, and queued ability-modifier foundation.

## Sprint 20: Fluid Pulse Combat Foundation

Replace immediate melee turns with a slower engagement loop that leaves room for skills and jutsus to carry combat.

- [x] Persist player-to-NPC engagements and resolve due auto attacks through a dedicated scheduler.
- [x] Keep basic auto attacks up close while preserving engagement across movement.
- [x] Avoid a dedicated flee command; movement is the spacing tool.
- [x] Add authored mongoose and crane stances with pulse, accuracy, and evasion tradeoffs.
- [x] Add a persisted one-shot modifier queue for future range, accuracy, damage, and status effects.
- [x] Add `combat` and `stance` discovery, editable help prose, regression coverage, and migration `14`.

### Done When

Players can engage a hostile NPC, reposition without ending combat, inspect range, switch authored stances, and receive slow scheduler-driven basic attacks while future skills and jutsus have a transactional modifier queue to build on.

## Sprint 16: Substitution Technique

Implement one defensive jutsu without widening into a general ability engine prematurely.

- [x] Define authored jutsu execution metadata: chakra cost, activation window, cooldown, and effect key.
- [x] Add a player command for activating `Substitution Technique`.
- [x] Consume chakra transactionally and reject activation when chakra is insufficient.
- [x] Persist active defensive state and cooldown expiry.
- [x] Resolve the next eligible hostile NPC strike through Substitution instead of applying damage.
- [x] Record successful Substitution resolution through the jutsu-progression helper.
- [x] Integrate expiry and cooldown handling with the existing world scheduler where needed.
- [x] Add tests for activation, insufficient chakra, defensive resolution, expiry, cooldowns, reconnect persistence, and rollback.
- [x] Run an isolated TCP smoke pass without disturbing the preserved database or an active server process.

### Done When

A player can spend chakra to prepare Substitution Technique, avoid one eligible hostile NPC strike during its active window, gain jutsu proficiency when the defense resolves, and respect a persisted cooldown.

## Sprint 17: Builder and Training Playground

Make authored content expansion practical without editing Python.

- [x] Replace placeholder `dig` with coordinate-aware overlay editing.
- [x] Add room-description editing for authored zones.
- [x] Add a compact admin workflow for authored NPC templates and spawns.
- [x] Build a training area that exercises melee, recovery, Throw, and Substitution Technique.
- [x] Add reload and persistence tests for edited content.

### Done When

An admin can build and reload a small training encounter through authored content tools without restarting the server.

## Sprint 18: Builder Editing Suite

Expand the current compact builder tools into an engaged in-game authoring workflow.

- [x] Add `buildzone` for one-step anchored zone creation with a usable starting room and `zonelist` for placement inspection.
- [x] Add `redit` for room titles, descriptions, exits, and room flags such as indoor, outdoor, and vacuum.
- [x] Retain `dig` as the brief coordinate-aware room-creation command.
- [x] Add `rstat` for inspecting room identity, coordinates, exits, and flags.
- [x] Add `medit` for NPC prose, behavior, health, combat values, and respawn timing.
- [x] Add `mstat` for NPC inspection.
- [x] Add `iedit` for item creation and modification.
- [x] Add `istat` for item inspection.
- [x] Add `spawnitem` so newly authored items can be placed as finite persistent seeds without editing JSON.

### Done When

An admin can create, inspect, and revise a small zone with rooms, NPCs, and items without editing Python or JSON directly.

## Sprint 19: Private Alpha Exercise

Exercise the playable loop before widening the feature surface.

- [ ] Add a repeatable two-client soak test for login, movement, chat, combat, disconnects, and reconnects.
- [ ] Run a private Linux test session through a firewall allowlist, private network, or VPN.
- [ ] Review runtime logs and fix the highest-impact failures.
- [ ] Decide whether encrypted transport is the next operational priority.

### Done When

The current loop survives a real private test session and produces actionable logs when something goes wrong.

## Builder Suite Recommendations

These are the next builder-focused slices after the private-alpha exercise. Favor the workflow and safety layer first; richer authored fields are much easier to add once builders can search, validate, and undo their work.

### Priority 1: Daily Authoring Workflow

- [ ] Add `zstat <zone>`, `rlist [zone]`, `mlist [zone]`, and `ilist [zone]` for compact zone inventories.
- [ ] Add `bfind <text>` to search rooms, NPCs, and items by key, title, name, keyword, or VNUM.
- [ ] Add `contentcheck [zone]` to report broken exits, overlapping coordinates, missing spawn templates, invalid VNUM references, duplicate keys, and out-of-bounds overlays before reload.
- [ ] Add `cloneitem`, `clonenpc`, and `cloneroom` for fast variations without repetitive field entry.
- [ ] Add `spawnlist`, `despawnitem`, and `despawnnpc` so authored seeds can be inspected and intentionally removed.

### Priority 2: Safer World Editing

- [ ] Add `redit link <direction> <vnum>` and `redit unlink <direction>` with optional reciprocal updates.
- [ ] Add guarded `rdelete` and `zdelete` commands that refuse removal while exits or spawns still reference the target.
- [ ] Add per-zone JSON backups and `bundo` for the most recent successful builder mutation.
- [ ] Add draft validation and explicit publish behavior before a zone edit reaches live overlays.
- [ ] Define room-flag behavior for indoor, outdoor, safe, no-combat, and recovery-friendly rooms.

### Priority 3: Richer Items and NPCs

- [ ] Add item values, weights, stack behavior, container support, and flags such as takeable, consumable, throwable, and unique.
- [ ] Add NPC loot tables, dialogue lines, room emotes, movement policy, leash radius, and aggression policy.
- [ ] Add reusable spawn groups with count, respawn timing, and room-distribution rules.
- [ ] Add template validation so unsupported item types, slots, NPC behaviors, and flags are rejected before persistence.
- [ ] Add builder audit records for who changed authored content, what changed, and when.

## Backlog

### Presentation and Navigation

- [ ] Add subcardinal directions and aliases: `sw`, `se`, `ne`, `nw`, `southwest`, `southeast`, `northeast`, and `northwest`.
- [ ] Make `survey` a wider map view, approximately `65x65`.
- [ ] Increase the regular view beyond the current `5x11` map.
- [ ] Add a clearer divider before the nearby-room contents display.
- [ ] Add map symbols for other players and NPCs.

### Skills and Jutsus

- [ ] Add a broader skill list with basic, advanced, ninjutsu, genjutsu, taijutsu, and kenjutsu placeholders. `skill` should show trained skills and `skill all` should show the full catalog with `[unimplemented]` markers.
- [ ] Expand the jutsu placeholder catalog to mirror skill discovery.

### World and Operations

- [ ] Add dimensions with independent grid sizes for planets, continents, and planes. Support dimension-aware `goto`, including `prime`.
- [ ] Create a batch script to copy runtime files to `D:\shared\Shinobi` for Linux-server transfer.
- [ ] Add a larger social-command library.
- [ ] Expand dialogue trees, quests, objectives, and rewards.
- [ ] Add NPC followers, factions, families, and friends.
- [ ] Add pets with growth and progression.
- [ ] Add more dynamic zones and unique areas.
- [ ] Create a broader live-management admin surface after builder tools mature.
- [ ] Optimize database queries only when profiling identifies a real bottleneck.
- [ ] Add encrypted transport before open-internet password testing.

## Design Boundaries

- Keep `(x, y)` coordinates canonical. VNUM rooms remain optional authored overlays.
- Add migrations and regression tests alongside each persistent system.
- Prefer one complete vertical slice over several partially connected systems.
- Keep adult-only or mature-consequence mechanics explicitly opt-in and separate from ordinary character state.
