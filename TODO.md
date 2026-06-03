# Shinobi MUD Active Roadmap

## Current Checkpoint

The private-alpha gameplay loop is covered by `177` automated tests. The current build has the builder and character foundation needed for a real soak pass:

- Coordinate-first wilderness movement with optional VNUM-backed overlays.
- Persistent accounts, items, inventories, equipment, NPC instances, combat state, body resources, descriptions, and point-based technique progress.
- Builder tools for zone inventory, search, validation, cloning, spawn inspection/removal, undo, and help publishing.
- Character-facing score/body/description, visible room-flag behavior, pulse combat, stances, Throw, and Substitution Technique.
- Editable command help and command categories with unpublished `(i)` markers.

Completed roadmap history now lives in [TODO-Historical.md](TODO-Historical.md). Detailed implementation notes remain in [CHANGELOG.md](CHANGELOG.md).

## Working Rules

Use this file as the active ordered implementation queue. Keep completed work out of this file once a sprint closes.

Each sprint should end with:

- Automated regression tests.
- A manual smoke-test path.
- README updates for player or admin behavior.
- A timestamped changelog entry.
- A focused Git commit.

Only keep one sprint active at a time. Reassess the order after each committed slice.

## Suggested Next Sprints

### Sprint 26: Private Alpha Soak Harness

Exercise the expanded builder and gameplay loop before widening the feature surface again.

- [ ] Add a repeatable two-client soak script for login, movement, chat, combat, disconnects, reconnect takeover, `prac`, `train`, `body`, and `rest`.
- [ ] Add a builder smoke path that uses `buildzone`, `zstat`, `rlist`, `bfind`, `contentcheck`, `cloneitem`, `cloneroom`, `spawnlist`, `despawnitem`, `bundo`, and `hedit publish`.
- [ ] Capture soak output and runtime logs into a local ignored artifact folder.
- [ ] Run a private Linux test session through a firewall allowlist, private network, or VPN.
- [ ] Review runtime logs and fix the highest-impact failures.
- [ ] Decide whether encrypted transport is the next operational priority.

#### Done When

The current loop survives a real private test session, and failures produce actionable logs instead of vague reports.

### Sprint 27: Builder Deletion, Links, and Publish Safety

Finish the safety layer around authored world mutations.

- [ ] Add `redit link <direction> <vnum>` and `redit unlink <direction>` with optional reciprocal updates.
- [ ] Add guarded `rdelete` and `zdelete` commands that refuse removal while exits or spawns still reference the target.
- [ ] Add draft validation and explicit zone publish behavior before a zone edit reaches live overlays.
- [ ] Expand builder audit records to include who changed authored content, what changed, when, and the zone file affected.
- [ ] Add tests for guarded deletion, reciprocal link/unlink, publish validation, audit records, and undo interaction.

#### Done When

Builders can link, unlink, delete, validate, publish, audit, and undo world edits without corrupting zone JSON or live overlays.

### Sprint 28: Rich Item and NPC Templates

Make authored objects and NPCs useful enough for richer training and starter-zone content.

- [ ] Add item values, weights, stack behavior, container support, and flags such as `takeable`, `consumable`, `throwable`, and `unique`.
- [ ] Add template validation for unsupported item types, slots, flags, NPC behaviors, and combat fields before persistence.
- [ ] Add NPC loot tables, dialogue lines, room emotes, movement policy, leash radius, and aggression policy.
- [ ] Add reusable spawn groups with count, respawn timing, and room-distribution rules.
- [ ] Update `iedit`, `istat`, `medit`, `mstat`, `spawnlist`, `contentcheck`, help, and README for the richer fields.

#### Done When

Builders can author richer starter items and NPCs in-game, validate them before reload, and inspect the resulting templates clearly.

### Sprint 30: Social Identity and Relationship Color Foundation

Prepare the player-name color system without pretending faction logic exists yet.

- [ ] Add a neutral relationship-state helper that currently resolves everyone as neutral.
- [ ] Render neutral player names in muted yellow in `who`, room presence, nearby listings, and map markers.
- [ ] Reserve friendly cyan and hostile magenta for future relationship/faction systems.
- [ ] Keep color output behind the existing `color on|off` behavior.
- [ ] Add tests for color-on/color-off player name rendering.

#### Done When

Player names have consistent neutral presentation everywhere, and the code has a clean future hook for friendly/hostile relationships.

## Backlog

### Skills and Jutsus

- [ ] Add a broader skill list with basic, advanced, ninjutsu, genjutsu, taijutsu, and kenjutsu placeholders.
- [ ] Expand the jutsu placeholder catalog to mirror skill discovery.
- [ ] Add `workout` or equivalent attribute-training loops after the practice/training model has soaked.
- [ ] Add more real skill and jutsu actions that consume stamina/chakra and raise fatigue.

### World and Operations

- [ ] Add dimensions with independent grid sizes for planets, continents, and planes. Support dimension-aware `goto`, including `prime`.
- [ ] Create a batch script to copy runtime files to `D:\shared\Shinobi` for Linux-server transfer.
- [ ] Add encrypted transport before open-internet password testing.
- [ ] Create a broader live-management admin surface after builder tools mature.
- [ ] Optimize database queries only when profiling identifies a real bottleneck.

### Content and Systems

- [ ] Add a larger social-command library.
- [ ] Expand dialogue trees, quests, objectives, and rewards.
- [ ] Add NPC followers, factions, families, and friends.
- [ ] Add pets with growth and progression.
- [ ] Add more dynamic zones and unique areas.

## Design Boundaries

- Keep `(x, y)` coordinates canonical. VNUM rooms remain optional authored overlays.
- Add migrations and regression tests alongside each persistent system.
- Prefer one complete vertical slice over several partially connected systems.
- Keep adult-only or mature-consequence mechanics explicitly opt-in and separate from ordinary character state.
- Prioritize builder safety, testability, and command discovery before adding broad content.
