# Shinobi MUD Active Roadmap

## Current Checkpoint

The private-alpha gameplay loop is covered by `201` automated tests. The current build has the builder and character foundation needed for a real soak pass:

- Coordinate-first wilderness movement with optional VNUM-backed overlays.
- Persistent accounts, items, inventories, equipment, NPC instances, combat state, body resources, descriptions, and point-based technique progress.
- Builder promotion plus builder tools for zone inventory, search, validation, publish, linking/unlinking, guarded deletion, cloning, rich template editing, spawn inspection/removal, undo, audit, and help publishing.
- Character-facing score/body/description, visible room-flag behavior, consent-backed social actions, Dex/Agi round combat, NPC stat sheets, stances, combat techniques, Throw, and Substitution Technique.
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

## Immediate Stabilization

Clear these before starting the next broad sprint.

- [x] Restore the `world.map` startup dependency so imports, tests, and local startup work again.
- [x] Hide backend percentages from active `prac <skill>` and `train <jutsu>` action output while keeping stored progress data intact.
- [x] Verify `rest` output stays player-facing and does not expose hidden backend percentages.
- [x] Re-run the full regression suite and a light manual smoke path.
- [x] Start Sprint 26 after the baseline is green.

## Recently Completed

- Sprint 26 added the local soak harness and builder smoke path.
- Sprint 27 added publish safety, guarded deletion, reciprocal links/unlinks, audit detail, and builder undo coverage.
- Sprint 28 added builder promotion, split builder/admin permissions, and rich item/NPC template metadata.
- Combat Techniques Sprint added stamina-based queued pulse techniques: Strike, Guard, Feint, and Recover.
- Round Combat and NPC Stat Sheets replaced slow pulse timing with Dex/Agi action rounds and gave NPCs player-like resources, stats, and authored technique hooks.
- Expansive Socials and Consent Foundation added catalog-backed social actions, consent settings, handholding movement, and opt-in restrictive states.

## Active Multi-Day Sprint Queue

### Sprint 29: Reusable Spawn Groups and Population Control

Turn single authored spawns into reusable population patterns that builders can use for rooms, mini-zones, and future patrol content.

- [ ] Add authored `item_spawn_groups` and `npc_spawn_groups` with `key`, template reference, count, room list, respawn timing, and distribution mode.
- [ ] Add migrations or persistence support only where needed; keep zone JSON as the authored source of truth.
- [ ] Add builder commands to create, inspect, validate, and remove spawn groups, with safe key validation and zone-local room validation.
- [ ] Expand `spawnlist` so it shows individual spawns and grouped spawns clearly.
- [ ] Expand `contentcheck` and `zpublish` to reject missing templates, invalid VNUMs, invalid counts, invalid respawn values, and unsupported distribution modes.
- [ ] Update `reloadcontent` so grouped spawns create stable seed keys without duplicating consumed finite items or living NPC instances.
- [ ] Add soak harness coverage for one builder-created item group and one NPC group.
- [ ] Update help, README, TODO, and CHANGELOG.

#### Test Plan

- Focused tests for JSON sync, `spawnlist`, `contentcheck`, publish refusal, duplicate reload protection, and builder command validation.
- Full suite with `python -m unittest discover -s tests -q`.
- Run `python soak_harness.py`.
- Run `python -m compileall -q .`, JSON validation, and `git diff --check`.

#### Done When

Builders can define repeated NPC/item population patterns without hand-authoring every individual seed, and reloads remain finite and duplication-safe.

### Sprint 30: Starter Content Arc and Builder-Usable Gameplay Loop

Use the richer template and spawn tooling to make Eve's Haven feel like a small playable training arc instead of a command test room.

- [ ] Add a compact starter objective chain using existing commands: find supplies, speak to a guide, practice Throw, train Substitution, defeat or avoid a practice construct, rest, and return.
- [ ] Add richer authored items using the new template metadata: non-takeable scenery, takeable supplies, a throwable weapon, a small reward, and at least one container-style item as metadata-only content.
- [ ] Add richer NPC templates using dialogue, room emotes, aggression policy, leash radius, and loot metadata.
- [ ] Use spawn groups for repeated supplies and practice targets once Sprint 29 is complete.
- [ ] Add a player-facing progress command or lightweight objective display only if the content loop needs it; do not build a full quest engine yet.
- [ ] Expand authored help or room prose so new players can discover `prac`, `train`, `throw`, `body`, `rest`, and `usejutsu substitution` naturally.
- [ ] Add regression tests for the starter route, key authored content, and no duplicate reloads.
- [ ] Update README with a concrete "first 15 minutes" path.

#### Test Plan

- Focused content tests for authored items, NPCs, spawns/groups, and route commands.
- Manual smoke: register, `look`, talk to guide, collect supplies, practice/train, fight or throw, rest, inspect inventory/body, return.
- Full suite, soak harness, compileall, JSON validation, and diff check.

#### Done When

A new private-alpha player can follow an in-world starter loop for movement, supplies, NPC interaction, practice, jutsu training, combat, and recovery without needing an external command list.

### Sprint 31: Social Identity and Relationship Color Foundation

Make player and character identity more readable while laying a clean hook for future factions and relationships.

- [ ] Add a neutral relationship-state helper that currently resolves everyone as neutral.
- [ ] Render neutral player names in muted yellow in `who`, room presence, nearby listings, local chat context, and map-related listings where names appear.
- [ ] Reserve friendly cyan and hostile magenta for future relationship/faction systems without exposing unfinished faction logic.
- [ ] Keep all color output behind the existing `color on|off` behavior.
- [ ] Add a compact social identity readout to `score` or `pstat` only if it helps builders verify state.
- [ ] Add tests for color-on/color-off rendering across `who`, room presence, nearby listings, and social output.
- [ ] Update help, README, TODO, and CHANGELOG.

#### Test Plan

- Focused presentation tests for sanitized ANSI output and color-disabled plain text.
- Multiplayer tests for two visible players and nearby listings.
- Full suite, compileall, JSON validation, and diff check.

#### Done When

Player names have consistent neutral presentation everywhere, color-disabled clients still receive clean text, and the code has a clear future hook for friendly/hostile relationships.

### Sprint 32: Private Linux Soak and Operations Hardening

Move from local confidence to a controlled private network test without opening the server recklessly.

- [ ] Create a repo script or documented command for packaging runtime files to `D:\shared\Shinobi` or another configured transfer folder.
- [ ] Add a preflight checklist for config, DB migration level, world map, zones, logs, firewall/VPN choice, and backup/archive paths.
- [ ] Add a private Linux smoke procedure that runs startup, login, movement, starter loop, builder promotion, builder validation, and shutdown/reconnect checks.
- [ ] Add log review guidance for runtime errors, failed auth, duplicate sessions, combat tick errors, and content sync errors.
- [ ] Decide whether encrypted transport must be implemented before any open-internet password testing; keep open-internet testing blocked until that decision is explicit.
- [ ] Add automation where useful, but keep destructive cleanup out of live data paths.
- [ ] Update README, TODO, CHANGELOG, and any transfer docs.

#### Test Plan

- Local full suite and soak harness before packaging.
- Manual Linux/private-network smoke with two test accounts and one promoted builder.
- Verify logs and DB migration level after the private test.
- Run `git diff --check` before closeout.

#### Done When

The game has a repeatable private Linux test path with clear preflight, transfer, smoke, rollback, and log-review steps, and open-internet exposure remains explicitly blocked until transport security is handled.

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

- [ ] Expand the social catalog with more authored normal, playful, intimate, and opt-in BDSM actions after the consent foundation soaks.
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
