# MUD Development TODO List

## High-Level Goals
- [ ] Stabilize core functionality (login, movement, map rendering).
- [ ] Implement advanced features (NPCs, combat, inventory).
- [ ] Enhance player interaction (prompts, chat, social features).

---

## Functionality

### Map/Movement
- [ ] Ensure proper movement functionality:
  - [ ] Handle boundary checks.
  - [ ] Validate player coordinates after movement.
- [ ] Fix/Enable "goto":
  - [ ] Add "goto grid" to allow players to jump to specific coordinates.
  - [ ] Add "goto player" to teleport to another player’s location.
- [ ] Ensure visibility of other players on the map.

### Player Prompt
- [ ] Add dynamic updates to the player prompt:
  - [ ] Display current health, stamina, and chakra.
  - [ ] Include player’s grid coordinates or room name.

### Location Tracking
- [ ] Add room name to the player prompt.
- [ ] Include room details in the "status" command.

---

## Features

### Player Commands
- [ ] Implement a "look" command:
  - [ ] Show surroundings based on grid position.
  - [ ] Include visible players, objects, and items.
- [ ] Add inventory commands:
  - [ ] "inventory" to list items.
  - [ ] "get" and "drop" for item management.
- [ ] Add "whisper" and "shout" for player communication.

### Combat System
- [ ] Basic melee combat:
  - [ ] Damage calculation based on player stats.
  - [ ] Health reduction and defeat logic.
- [ ] Add a turn-based combat system.
- [ ] Include basic NPC enemies with simple AI.

---

## Quality of Life Improvements

### User Interface
- [ ] Beautify the map rendering:
  - [ ] Add borders or separators for better readability.
  - [ ] Highlight player’s position clearly.
- [ ] Create a help command:
  - [ ] List all available commands and their syntax.

### Database Integration
- [ ] Automate schema updates (e.g., adding new fields).
- [ ] Optimize player data queries for performance.

---

## Testing and Debugging
- [ ] Develop unit tests for core functionality:
  - [ ] Movement and boundary checks.
  - [ ] Command parsing and execution.
- [ ] Set up logging for easier debugging:
  - [ ] Log player actions (movement, commands, combat).
  - [ ] Highlight errors and warnings.

---

## Long-Term Goals
- [ ] Design NPC interaction system:
  - [ ] Dialogue trees for player-NPC interactions.
  - [ ] Quest system with objectives and rewards.
- [ ] Expand the map with dynamic zones:
  - [ ] Implement a transition system for large-scale maps.
  - [ ] Add unique areas with special features.
- [ ] Create a robust admin panel for live game management.

---

## Notes
- Use this document to track progress and prioritize tasks.
- Mark completed tasks with `[x]`.
- Add new ideas or features under their respective categories.

