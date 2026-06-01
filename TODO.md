# Shinobi MUD Active Roadmap

## Current State

The foundation checkpoint in `FOUNDATION_CHECKLIST.md` is complete.

- [x] Stabilize account registration, login, disconnects, and reconnects.
- [x] Stabilize coordinate-first movement and world-map rendering.
- [x] Add local multiplayer chat, global OOC chat, `who`, `score`, and `loc`.
- [x] Add metadata-driven commands, automatic unique-prefix matching, and `help`.
- [x] Drop Eve's Haven onto the wilderness grid as the first VNUM-backed overlay zone.
- [x] Add versioned database migrations and automated tests for the core loop.

---

## Phase 7: Private Alpha Hardening

Improve operational confidence before adding systems with larger state surfaces.

- [x] Write timestamped runtime logs under `logs/` for each server launch.
- [x] Log unexpected reactor failures in the existing per-launch runtime log.
- [x] Add Linux deployment notes and a `systemd` service example.
- [x] Disable `copyover` until reconnect-based restarts need improvement.

### Deferred Until Needed

- [ ] Add a repeatable two-client soak test for login, movement, chat, disconnects, and reconnects.
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

- [ ] Add basic melee attacks against NPCs.
- [ ] Calculate damage from player stats.
- [ ] Apply health reduction, defeat, and recovery logic.
- [ ] Decide whether the first combat loop is cooldown-based or turn-based.
- [ ] Add one simple NPC enemy with minimal AI.
- [ ] Add tests for damage, defeat, invalid targets, and disconnect behavior.

---

## Communication and Social Backlog

- [ ] Add `whisper`.
- [ ] Add `shout`.
- [ ] Add a larger social-command library.
- [ ] Design richer roleplay socials, including optional mature consequence systems.

---

## Builder and Admin Backlog

- [x] Add `goto <vnum>` for authored overlay rooms.
- [x] Add `zoneinfo [vnum]`.
- [x] Add `placezone <zone_file> <x> <y>`.
- [x] Add `reloadcontent` for applying authored JSON edits to live templates and missing spawns.
- [ ] Replace placeholder `dig` with coordinate-aware overlay editing.
- [ ] Add room-description editing for authored zones.
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
