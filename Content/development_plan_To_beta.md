# Development Plan: Beta Roadmap for Shinobi MUD

## Stage 1: Core World and Systems Setup
### 1.1 World Grid and Zones
- **Task**: Implement the world grid and overlay zones.
  - Create a `world_grid` data structure to track global coordinates.
  - Overlay `zone` definitions on the grid (e.g., forests, towns).
  - Integrate grid data into the `find_zone_by_vnum` and `goto` systems.

- **Dependencies**:
  - Refactor zone management (`utils.py`) to support grid-based lookups.
  - Expand admin commands for creating, resizing, and linking zones.
  - Introduce edge-case handling for players moving outside valid grid areas.

---

### 1.2 Basic Combat System
- **Task**: Establish the foundation for real-time combat.
  - Implement a **turn processor** or **combat loop** to manage action timing.
  - Develop basic **hitroll** and **damroll** calculations.
  - Add defensive and offensive stances that modify combat performance.

- **Steps**:
  - Create a `combat_state` object to track active battles.
  - Add combat-related commands:
    - **Attack**: Engage in melee or ranged attacks.
    - **Defend**: Take a defensive stance, reducing damage.
    - **Flee**: Exit combat.
  - Integrate with the **character sheet** for stat-based calculations (e.g., Strength, Dexterity).

- **Dependencies**:
  - Extend the player status system for tracking health, stamina, and chakra in combat.
  - Enhance NPC AI to support basic combat actions.

---

### 1.3 Stances and Styles
- **Task**: Design the stance system and its effects.
  - Add core stances (Offensive, Defensive, Balanced).
  - Add style modifiers for future integration (e.g., Taijutsu, Kenjutsu).

- **Steps**:
  - Create a `stance` attribute for players and NPCs.
  - Define **stance effects**:
    - Offensive: +Damage, -Defense.
    - Defensive: +Defense, -Speed.
    - Balanced: No modifiers, but reduced cooldowns.
  - Develop command-based stance switching (`stance offensive`).

- **Dependencies**:
  - Expand the combat loop to account for stances.

---

### 1.4 Enhanced Character Sheet
- **Task**: Build a more detailed character sheet with editable stats.
  - Add a comprehensive character status overview:
    - Stats: Health, Stamina, Chakra.
    - Attributes: Strength, Dexterity, Intelligence, etc.
    - Chakra Release: Display elemental affinity.

- **Steps**:
  - Refactor the `status` command to include the above.
  - Introduce admin commands for modifying stats directly.

---

## Stage 2: Gameplay Enhancements
### 2.1 World Tick and Calendar System
- **Task**: Implement a real-time tick system for time progression.
  - Add support for:
    - Day/night cycles.
    - Calendar events (e.g., festivals, invasions).
    - Rest mechanics for players (e.g., regen health during sleep).

- **Steps**:
  - Develop a `world_clock` module to track global time.
  - Trigger time-based effects (e.g., faster chakra regen at night).
  - Update zone and NPC behaviors based on time.

---

### 2.2 Social and General Commands
- **Task**: Expand the social and general interaction systems.
  - Add new social commands:
    - **Whisper**: Send private messages to players in the same room.
    - **Yell**: Broadcast to adjacent rooms.
    - **Pose**: Perform custom emotes.
  - Refactor existing commands (`say`, `ooc`, `emote`) to include logging and range.

- **Dependencies**:
  - Update the `players_in_rooms` structure to support ranged communication.

---

### 2.3 Help File System
- **Task**: Create an in-game help command.
  - Allow players to type `help <topic>` to retrieve guidance.
  - Use a JSON-based help file structure for easy additions.

- **Steps**:
  - Add a `help.json` file to store topics and descriptions.
  - Develop a `help` command to search and display entries.

---

### 2.4 Improved Admin Commands
- **Task**: Enhance tools for building and debugging the game.
  - Add commands for:
    - Copying and linking zones.
    - Inspecting player stats (`inspect <player>`).
    - Managing the world tick (e.g., `set_time`, `pause_tick`).
  - Refactor the `copyover` system for better state recovery.

---

### 2.5 Movement and Command Processing
- **Task**: Improve player movement and command efficiency.
  - Add **command shortcuts** (e.g., `l` for `look`, `n` for `north`).
  - Allow **compound commands** (e.g., `look at <object>`).

- **Steps**:
  - Update the `process_command` function to handle shortcuts and arguments.
  - Add robust error handling for invalid input.

---

## Stage 3: Expanded Systems
### 3.1 Advanced Combat Features
- **Task**: Build on the basic combat system with special abilities and proficiencies.
  - Add abilities that scale with stats (e.g., faster jutsu with higher Chakra Control).
  - Include cooldowns and timers for powerful moves.

- **Steps**:
  - Expand the `combat_state` object to track ability usage.
  - Create a **proficiency formula** based on:
    - Dexterity + Chakra Infused Speed + Elemental Affinity.

---

### 3.2 RTS-Like Leadership Mechanics (Stretch Goal)
- **Task**: Introduce the foundation for player-managed factions.
  - Allow players to control territories, build defenses, and recruit troops.

---

## Prioritized Next Steps
1. **World Grid and Zones**:
   - Implement the grid system and link it with zone management.
2. **Basic Combat**:
   - Focus on hitroll, damroll, and stances.
3. **Enhanced Character Sheet**:
   - Ensure stats and attributes are visible and modifiable.
4. **Tick System**:
   - Build a framework for real-time progression.
5. **Help System**:
   - Provide in-game support for new players.

---

## Summary
This plan provides a comprehensive guide to reaching **beta mode** by focusing on the foundational systems (world, combat, and progression) while laying the groundwork for future expansions like RTS mechanics and advanced combat features. Each stage builds logically on the previous, ensuring scalable development.
