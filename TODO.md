# Shinobi MUD Active Roadmap

## Current State

The foundation checkpoint in `FOUNDATION_CHECKLIST.md` is complete.

- [x] Stabilize account registration, login, disconnects, and reconnects.
- [x] Stabilize coordinate-first movement and world-map rendering.
- [x] Add local multiplayer chat, global OOC chat, `who`, `score`, and `loc`.
- [x] Add metadata-driven commands, automatic unique-prefix matching, and `help`.
- [x] Drop Eve's Haven onto the wilderness grid as the first VNUM-backed overlay zone.
- [x] Add versioned database migrations and automated tests for the core loop.
- [x] Add ANSI presentation styling with a session-level `color on|off` toggle.
- [x] Add abstract body resources, short-rest recovery, private whispers, and nearby shouts.

### Current Checkpoint

The private-alpha gameplay loop is covered by 105 automated tests. Runtime database ownership is explicit: the server keeps a maintenance connection for startup and ticks, while each connected player session owns and closes its own connection. The next recommended step is the Body Resource Integration checkpoint before Sprint 15.

---

## Planning Approach

Use this file as the active ordered roadmap. The documents under `Content/` remain design references for the larger vision, but they are not the current implementation queue.

Work in small milestone sprints rather than fixed calendar sprints. Each sprint should deliver one testable vertical slice and end with:

- Automated regression tests.
- A manual smoke-test path.
- Updated README documentation when player or admin behavior changes.
- A changelog entry.
- A focused Git commit.

Only keep one sprint active at a time. Reassess the order after each sprint when new dependencies become visible.

---

## Phase 7: Private Alpha Hardening

Improve operational confidence before adding systems with larger state surfaces.

- [x] Write timestamped runtime logs under `logs/` for each server launch.
- [x] Log unexpected reactor failures in the existing per-launch runtime log.
- [x] Add Linux deployment notes and a `systemd` service example.
- [x] Disable `copyover` until reconnect-based restarts need improvement.

### Deferred Until Needed

- [ ] Add a repeatable two-client soak test for login, movement, chat, disconnects, and reconnects. Scheduled for Sprint 17.
- [ ] Add encrypted transport before any open-internet password testing.

### Private Alpha Status

Ready for trusted private Linux alpha sessions through a firewall allowlist, private network, or VPN. Complete the deferred items before broader testing.

---

## Phase 8: Player Feedback and Navigation

Make the existing world easier to read before adding inventory or combat.

- [x] Add a player prompt with health, stamina, chakra, and current coordinates or authored room name.
- [x] Include current coordinates and authored room details in `score`.
- [x] Beautify map output with a compact border or legend while keeping the player marker clear.
- [x] Add optional nearby-player listings within a configurable radius, defaulting to 20 grid cells.
- [x] Add an admin or config toggle for nearby-player listings.
- [x] Add `goto grid <x> <y>` for admins.
- [x] Add `goto player <name>` for admins.

### Done When

Players can orient themselves quickly, and admins can move around the coordinate world deliberately during live tests.

---

## Phase 9: Inventory and Room Objects

Introduce the first persistent gameplay state beyond character fields and locations.

- [x] Define item, room-object, and character-inventory storage.
- [x] Show visible objects and items in `look`.
- [x] Add `inventory`, `get`, and `drop`.
- [x] Add a few sample items in Eve's Haven.
- [x] Add migrations and automated tests for persistence, reconnects, and invalid item operations.

### Done When

Players can see, pick up, carry, drop, disconnect with, and recover a small set of persistent items safely.

---

## Phase 10: NPC Foundation

Add NPC presence before combat rules.

- [x] Define JSON-authored NPC templates and SQLite-backed spawned NPC instances.
- [x] Display NPCs in `look`.
- [x] Add a minimal world tick scheduler for NPC updates.
- [x] Add one simple Eve's Haven NPC with `talk <character>`.
- [x] Add tests for spawning, visibility, restart behavior, dialogue, and ticking.

### Done When

One authored NPC can exist, appear in a room, survive expected restart behavior, and respond to a basic interaction.

---

## Phase 11: Combat Slice

Build combat only after inventory and NPC state are reliable.

- [x] Add basic melee attacks against NPCs.
- [x] Calculate damage from player stats.
- [x] Apply health reduction, defeat, and recovery logic.
- [x] Use a command-driven turn model: one player strike, then one surviving hostile counterattack.
- [x] Add one simple NPC enemy with minimal AI.
- [x] Add tests for damage, defeat, invalid targets, and disconnect behavior.

### Done When

One authored hostile NPC can be attacked, counterattack, recover after defeat, and preserve combat state safely across disconnects.

---

## Sprint 12: Inventory Management and Presentation

Turn the persistent-item proof of concept into a usable interaction layer before combat begins depending on equipment.

- [x] Add authored item keywords, item types, and interaction metadata without moving mutable instances out of SQLite.
- [x] Resolve item targets predictably: exact names first, then authored keywords and prefixes, then the first stable matching instance.
- [x] Add ordinal targeting such as `2.kun` when duplicate items need an explicit selection.
- [x] Add `examine <item>` and `look at <item>` for items in the room or character inventory.
- [x] Improve `inventory` formatting so carried items and equipped items are easy to scan.
- [x] Add equipment storage and basic `wield <item>` and `remove <item>` commands.
- [x] Define the Practice Kunai as an authored weapon/tool that can be examined and wielded.
- [x] Defer thrown-kunai attacks until the combat reliability sprint has a deliberate ranged-targeting rule.
- [x] Clean up room presentation: group map, room header, description, exits, items, NPCs, and players into readable sections.
- [x] Decide whether normal `look` and movement should use a compact local map while `survey` provides the larger terrain view.
- [x] Avoid noisy empty-state lines such as `You are alone in this room.` when the rest of the room output already reads cleanly.
- [x] Add tests for item targeting, duplicate selection, examination, equipment persistence, and formatted room output.

### Done When

Players can identify, inspect, pick up, carry, drop, and wield authored items with abbreviated targeting, and room output is compact enough to read during normal play.

---

## Sprint 13: Combat Reliability

Turn the Phase 11 proof of concept into a dependable base for later ninja abilities.

- [x] Define current and maximum health semantics for players and NPCs.
- [x] Add hit chance using attacker and defender stats instead of guaranteed melee hits.
- [x] Apply equipped-weapon metadata to basic attacks without hardcoding kunai behavior in Python.
- [x] Broadcast attacks, damage, and defeats to other players at the same location.
- [x] Add `consider <character>` or equivalent combat inspection.
- [x] Add a deliberate recovery rule for player defeat, including location behavior.
- [x] Add transaction and multiplayer tests for two players attacking the same NPC.

### Done When

Two players can fight the same authored NPC without state corruption, nearby players understand what happened, and health behavior is explicit enough to support abilities.

---

## Sprint 14: Character Foundation

Repair the rough character-creation flow before adding progression systems that depend on it.

- [x] Replace the current incremental stat-allocation prompt with a clearer allocation workflow.
- [x] Separate current resources from maximum health, stamina, and chakra.
- [x] Decide the initial clan and natural-release data model.
- [x] Display the new character fields in `score`.
- [x] Add migrations and tests for new accounts and existing-account upgrades.

### Done When

New players can create understandable ninja characters, and existing private-alpha accounts migrate without losing progress.

---

## Presentation QoL Checkpoint

- [x] Add semantic ANSI styling for prompts, room blocks, maps, and social-channel metadata.
- [x] Add `color on|off` as a session-level player preference.
- [x] Keep plain output available for clients that do not render ANSI colors cleanly.
- [x] Strip terminal control sequences from player-authored chat and emotes.
- [x] Add regression tests for colored output, plain output, toggling, and chat sanitization.

---

## Runtime State Ownership Checkpoint

Clean up initialization and database ownership before adding scheduler-driven ability state. Keep this sprint focused on lifecycle boundaries; do not redesign gameplay systems.

- [x] Remove database creation from module import side effects.
- [x] Keep one explicit server-maintenance connection for initialization, validation, authored-content synchronization, and world ticks.
- [x] Replace the shared module-level SQLite cursor passed to every protocol with factory-created per-session connections.
- [x] Close protocol-owned connections on disconnect without closing injected test connections.
- [x] Avoid departure broadcasts for sessions that disconnect before joining a tracked room.
- [x] Confirm world ticks and player commands perform database work without relying on one long-lived shared cursor.
- [x] Preserve startup validation, reconnect behavior, migrations, and all existing gameplay output.
- [x] Add regression tests for factory sessions, disconnect cleanup, repeated server initialization, player commands, and world ticks.
- [x] Document the maintenance-versus-session connection lifecycle in the README.

### Done When

Server startup, player sessions, and scheduled world ticks have clear database ownership; repeated initialization remains testable; and the existing private-alpha loop still passes its regression suite.

### Why This Comes First

Sprint 15 introduces cooldowns, cast timing, and scheduler integration. Establishing runtime-state ownership first keeps those timed writes from depending on the current shared-cursor and import-order behavior.

---

## Body and Social Foundation Checkpoint

- [x] Persist abstract nutrition, hydration, fatigue, and recovery-readiness fields.
- [x] Add `body` and `rest` so players can inspect condition and deliberately recover stamina and chakra.
- [x] Increase fatigue through ordinary movement and valid hostile combat turns.
- [x] Add private online `whisper` messages.
- [x] Add nearby `shout` messages for the current and adjacent grid coordinates.
- [x] Strip terminal control sequences from the new player-authored social messages.
- [x] Add migration and regression coverage for body recovery, exertion, whispering, shouting, and sanitization.

### Deferred Adult-Only Design

- [ ] Define any reproductive or mature-consequence mechanics as an explicit adult-only, opt-in roleplay module before implementation.
- [ ] Keep ordinary character creation and body recovery independent from any mature systems.

---

## Recommended Next Step: Body Resource Integration

Turn the body-resource foundation into a complete gameplay loop before adding chakra abilities.

- [ ] Add authored food and drink consumables.
- [ ] Add `eat <item>` and `drink <item>` interactions.
- [ ] Decide the consequences of low nutrition, low hydration, and high fatigue.
- [ ] Tune travel, combat, and rest costs through focused tests.
- [ ] Keep the model abstract enough to support future medical and roleplay extensions.

### Done When

Players can spend and restore body resources deliberately, and the consequences are clear enough for chakra recovery to build on them.

---

## Sprint 15 - First Chakra Ability

Add one complete ninja ability after the runtime-state cleanup and the existing combat and character foundations are stable.

- [ ] Define authored ability data for chakra cost, range, cast time, cooldown, and effect.
- [ ] Add one offensive jutsu and one defensive response.
- [ ] Consume chakra and restore it through a deliberate recovery rule.
- [ ] Integrate ability timing with the world scheduler.
- [ ] Add tests for casting, cooldowns, insufficient chakra, and defensive timing.

### Done When

Players can use and counter one chakra-driven ability without bypassing the combat rules established in Sprint 13.

---

## Sprint 16: Builder and Training Playground

Make it practical to expand content without editing Python.

- [ ] Replace placeholder `dig` with coordinate-aware overlay editing.
- [ ] Add room-description editing for authored zones.
- [ ] Add a small admin workflow for creating or updating authored NPC templates and spawns.
- [ ] Build a compact training area that exercises melee, recovery, and the first chakra ability.
- [ ] Add reload and persistence tests for edited content.

### Done When

An admin can build a small training encounter through authored content tools and reload it without restarting the server.

---

## Sprint 17: Private Alpha Exercise

Exercise the playable loop before widening the feature surface.

- [ ] Add a repeatable two-client soak test for login, movement, chat, combat, disconnects, and reconnects.
- [ ] Run a private Linux test session through a firewall allowlist, private network, or VPN.
- [ ] Review runtime logs and fix the highest-impact failures.
- [ ] Decide whether encrypted transport is the next operational priority.

### Done When

The current game loop survives a real private test session and produces actionable logs when something goes wrong.

---

## Communication and Social Backlog

- [x] Add `whisper`.
- [x] Add `shout`.
- [ ] Add a larger social-command library.
- [ ] Design richer roleplay socials, including explicit adult-only opt-in mature consequence systems.

---

## Builder and Admin Backlog

- [x] Add `goto <vnum>` for authored overlay rooms.
- [x] Add `zoneinfo [vnum]`.
- [x] Add `placezone <zone_file> <x> <y>`.
- [x] Add `reloadcontent` for applying authored JSON edits to live templates and missing spawns.
- [ ] Replace placeholder `dig` with coordinate-aware overlay editing. Scheduled for Sprint 16.
- [ ] Add room-description editing for authored zones. Scheduled for Sprint 16.
- [ ] Create a robust live-management admin surface after command-line builder tools mature.

---

## Later Ideas

- [ ] Dialogue trees, quests, objectives, and rewards.
- [ ] NPC followers, factions, families, and friends.
- [ ] Pets with growth and progression.
- [ ] Additional dynamic zones and unique areas.
- [ ] Optimize database queries when profiling identifies a real bottleneck.

---

## Notes

- Keep `(x, y)` coordinates canonical. VNUM rooms remain optional authored overlays.
- Add migrations and automated tests alongside each persistent system.
- Prefer one complete vertical slice over several partially connected systems.
- Keep the runtime-state cleanup narrow: lifecycle ownership first, broader architecture changes only when a failing test or Sprint 15 requirement justifies them.
