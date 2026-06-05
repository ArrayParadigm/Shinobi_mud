# Veilborn MUD Historical Roadmap

This file holds completed TODO and sprint history moved out of the active roadmap. Current work lives in [TODO.md](TODO.md). Detailed implementation notes live in [CHANGELOG.md](CHANGELOG.md).

## Completed Checkpoints

- [x] Account lifecycle, permissions, password hashing, and migrations.
- [x] Coordinate-first movement, overlays, player feedback, and multiplayer basics.
- [x] Persistent inventories, equipment, authored NPCs, melee combat, and combat reliability.
- [x] Character foundation, ANSI presentation, runtime database ownership, and body resources.
- [x] Food and drink consumption with recovery consequences.
- [x] Usage-based skill and expression framework with discoverable placeholder catalogs.
- [x] First real skill action: `Throw`.
- [x] First real expression action: `Substitution Expression`.
- [x] Coordinate-overlay builder and compact training playground.
- [x] Builder-editable help prose and categorized command discovery.
- [x] Sprint 18 builder editing suite.
- [x] Player inspection and validated player-setting administration.
- [x] Pulse combat engagements, authored stances, and queued ability-modifier foundation.
- [x] Neutral S1-S5 stance profiles with opposed accuracy/evasion tradeoffs and damage reduction.
- [x] MISC priority pass: reconnect takeover, connection announcements, player feedback files, default-10 character creation, builder help coverage, and easier NPC targeting.
- [x] Sprint 21 builder daily workflow: zone stats, room/NPC/item lists, builder search, and content validation.
- [x] Sprint 22 builder safety and help publishing: clone, spawn inspect/remove, undo snapshots, and `hedit`.
- [x] Sprint 23 character identity and score: descriptions, vertical resources, stat display aliases, and admin exposure.
- [x] Sprint 24 body, stats, and room flags: stat-informed recovery and visible room-flag consequences.
- [x] Sprint 25 practice and training progression: hidden point thresholds, milestone messaging, and expanded `prac`/`train`.
- [x] Sprint 29 presentation and navigation upgrade: diagonal movement, larger maps, population markers, nearby divider, and command/argument coloring.

## Sprint 16: Substitution Expression

Implemented one defensive expression without widening into a general ability engine prematurely.

- [x] Define authored expression execution metadata: wisp cost, activation window, cooldown, and effect key.
- [x] Add a player command for activating `Substitution Expression`.
- [x] Consume wisp transactionally and reject activation when wisp is insufficient.
- [x] Persist active defensive state and cooldown expiry.
- [x] Resolve the next eligible hostile NPC strike through Substitution instead of applying damage.
- [x] Record successful Substitution resolution through the expression-progression helper.
- [x] Integrate expiry and cooldown handling with the existing world scheduler where needed.
- [x] Add tests for activation, insufficient wisp, defensive resolution, expiry, cooldowns, reconnect persistence, and rollback.
- [x] Run an isolated TCP smoke pass without disturbing the preserved database or an active server process.

### Done When

A player can spend wisp to prepare Substitution Expression, avoid one eligible hostile NPC strike during its active window, gain expression proficiency when the defense resolves, and respect a persisted cooldown.

## Sprint 17: Builder and Training Playground

Made authored content expansion practical without editing Python.

- [x] Replace placeholder `dig` with coordinate-aware overlay editing.
- [x] Add room-description editing for authored zones.
- [x] Add a compact admin workflow for authored NPC templates and spawns.
- [x] Build a training area that exercises melee, recovery, Throw, and Substitution Expression.
- [x] Add reload and persistence tests for edited content.

### Done When

An admin can build and reload a small training encounter through authored content tools without restarting the server.

## Sprint 18: Builder Editing Suite

Expanded compact builder tools into an engaged in-game authoring workflow.

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

## Sprint 20: Fluid Pulse Combat Foundation

Replaced immediate melee turns with a slower engagement loop that leaves room for skills and expressions to carry combat.

- [x] Persist player-to-NPC engagements and resolve due auto attacks through a dedicated scheduler.
- [x] Keep basic auto attacks up close while preserving engagement across movement.
- [x] Avoid a dedicated flee command; movement is the spacing tool.
- [x] Add five neutral authored stance profiles with accuracy, damage, evasion, and damage-reduction tradeoffs.
- [x] Add a persisted one-shot modifier queue for future range, accuracy, damage, and status effects.
- [x] Add `combat` and `stance` discovery, editable help prose, regression coverage, and migration `14`.

### Done When

Players can engage a hostile NPC, reposition without ending combat, inspect range, switch authored stances, and receive slow scheduler-driven basic attacks while future skills and expressions have a transactional modifier queue to build on.

## Sprint 21: Builder Daily Workflow

- [x] Add compact builder inventory commands: `zstat <zone>`, `rlist [zone]`, `mlist [zone]`, and `ilist [zone]`.
- [x] Add `bfind <text>` across rooms, templates, spawns, titles/names, keywords, and VNUMs.
- [x] Add `contentcheck [zone]` for broken exits, duplicate VNUMs, overlapping coordinates, missing templates, invalid VNUMs, and out-of-bounds overlays.

### Done When

Builders can inspect and validate a zone without opening JSON.

## Sprint 22: Builder Safety and Help Publishing

- [x] Add `cloneitem`, `clonenpc`, and `cloneroom`.
- [x] Add `spawnlist`, `despawnitem`, and `despawnnpc`.
- [x] Add per-zone undo snapshots before successful builder mutations and `bundo`.
- [x] Add `hedit` with summary/detail/category/publish/unpublish behavior and unpublished `(i)` markers.

### Done When

Builders can safely create, inspect, undo, and publish help without editing files manually.

## Sprint 23: Character Identity and Score

- [x] Add persisted character descriptions and player-facing description view/edit commands.
- [x] Rework `score` into vertical resources, qualitative fatigue, horizontal stats, and description output.
- [x] Map displayed `Intellect` and `Condition` onto existing DB-compatible fields.
- [x] Update admin `pstat`/`pset` for descriptions and stat aliases.

### Done When

New and existing characters have readable identity, description, and score output.

## Sprint 24: Body, Stats, and Room Flags

- [x] Apply v1 stat effects to recovery, wisp support, fatigue tolerance, and existing combat calculations.
- [x] Implement room-flag behavior for `indoor`, `outdoor`, `vacuum`, `darkness`, `brightness`, `safe`, `no-combat`, and `recovery-friendly`.
- [x] Apply minimap/survey behavior for darkness, brightness, and indoor spaces.
- [x] Apply vacuum fatigue and health pressure through the existing body system.

### Done When

Room flags have visible, testable player consequences.

## Sprint 25: Practice and Training Progression

- [x] Rework `prac <skill>` and `train <expression>` into progression actions.
- [x] Convert skill/expression progress to hidden point thresholds while preserving tier/percent display.
- [x] Use thresholds from `Untrained` through capped `Grandmaster`.
- [x] Add milestone messages at 10% improvements and tier changes.

### Done When

`prac throw` and `train substitution` advance through the new progression model with tests.

## Sprint 29: Presentation and Navigation Upgrade

- [x] Add subcardinal directions and aliases: `sw`, `se`, `ne`, `nw`, `southwest`, `southeast`, `northeast`, and `northwest`.
- [x] Increase the normal `look` minimap beyond the compact view to an `11x11` outdoor view.
- [x] Keep `survey` at a wider view while tuning it to a readable rectangular scan.
- [x] Add a clearer divider before nearby-room contents.
- [x] Add map symbols for other players and NPCs.
- [x] Adjust command/help colors so commands and args are visually distinct from descriptions.

### Done When

Players can navigate and scan populated rooms more easily without opening builder tools or reading dense raw output.

## Completed Starred and MISC Items

- [x] Add login/disconnect announcements MUD wide for all players.
- [x] Add room flags and their function: indoor, outdoor, vacuum, darkness, brightness, safe/no-combat, and recovery-friendly.
- [x] Reestablish attributes and resource definitions for health, stamina, wisp, fatigue, and stat display.
- [x] Disconnect/reconnect handling, including taking back over an already connected character.
- [x] Organize `score` as vertical resources and horizontal stats.
- [x] Rework stat display and v1 stat effects: Condition, Strength, Intellect, Dexterity, and Agility.
- [x] Support easier item and NPC targeting through prefixes and ordinals.
- [x] Add `suggest`, `bug`, `suggestions.md`, `bugs.md`, and `ai_suggestions.md`.
- [x] Rework character creation to default stats and attributes to `10`.
- [x] Add character descriptions with persisted defaults and edit/view commands.
- [x] Add help files for every builder command.
- [x] Make `help` show the same categorical breakdown as `commands`.
- [x] Mark unpublished help with `(i)`.
- [x] Add `hedit` for help summary/detail/category/publish/unpublish.
- [x] Rework `prac` and `train` into point-based practice/training actions with visible tier/percent display.

## Completed Builder Suite Recommendations

- [x] Add `zstat <zone>`, `rlist [zone]`, `mlist [zone]`, and `ilist [zone]` for compact zone inventories.
- [x] Add `bfind <text>` to search rooms, NPCs, and items by key, title, name, keyword, or VNUM.
- [x] Add `contentcheck [zone]` to report broken exits, overlapping coordinates, missing spawn templates, invalid VNUM references, duplicate keys, and out-of-bounds overlays before reload.
- [x] Add `cloneitem`, `clonenpc`, and `cloneroom` for fast variations without repetitive field entry.
- [x] Add `spawnlist`, `despawnitem`, and `despawnnpc` so authored seeds can be inspected and intentionally removed.
- [x] Add per-zone JSON backups and `bundo` for the most recent successful builder mutation.
- [x] Define room-flag behavior for indoor, outdoor, safe, no-combat, and recovery-friendly rooms.
