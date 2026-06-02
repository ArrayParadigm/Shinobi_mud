# Shinobi MUD Active Roadmap

## Current Checkpoint

The private-alpha gameplay loop is covered by `140` automated tests. The current build includes:

- Coordinate-first wilderness movement with Eve's Haven as a VNUM-backed overlay zone.
- Persistent accounts, items, inventories, equipment, NPC instances, combat state, and body resources.
- Independent SQLite connections for server maintenance and connected player sessions.
- ANSI presentation, social commands, food and drink consumption, and deliberate recovery.
- Authored skill and jutsu catalogs with usage-based `0-100%` proficiency.
- `skill`, `prac`, `jutsu`, and `train` discovery commands with `[unimplemented]` catalog placeholders.
- A real `throw <item> at <character>` action. Practice Kunai throws deal `3` damage, add `2` fatigue, land at the target location, and raise `Throw` proficiency on valid hits or misses.
- A real `usejutsu substitution` action. It spends `3` chakra, prepares a `30` second defensive window, avoids the next eligible hostile NPC strike, raises Substitution proficiency on resolution, and persists a `60` second cooldown.
- Coordinate-aware builder commands for digging rooms, editing descriptions, creating basic NPC templates, and seeding persistent NPC spawns.
- A complete `commands` catalog generated from registered help metadata.
- Builder-editable command summaries and detailed help prose loaded from `helpfiles/commands.json`.

The next step is exercising the current loop through a private-alpha soak pass.

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

## Sprint 18: Private Alpha Exercise

Exercise the playable loop before widening the feature surface.

- [ ] Add a repeatable two-client soak test for login, movement, chat, combat, disconnects, and reconnects.
- [ ] Run a private Linux test session through a firewall allowlist, private network, or VPN.
- [ ] Review runtime logs and fix the highest-impact failures.
- [ ] Decide whether encrypted transport is the next operational priority.

### Done When

The current loop survives a real private test session and produces actionable logs when something goes wrong.

## Backlog

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
