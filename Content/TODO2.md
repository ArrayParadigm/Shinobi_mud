# Development Route Plan

## Introduction
This plan outlines a **development sequence** for Shinobi MUD, focusing on creating core systems first, iterating on them, and gradually building toward advanced features like expansions and RTS mechanics. Each phase includes objectives, key tasks, and dependencies.

---

## Phase 1: Core Framework and Ninja Gameplay (MVP)
### Objectives
- Establish the foundational mechanics, ensuring the game is playable with basic combat, progression, and character creation.
- Build the **grid-based combat system** and core ninja abilities.

### Key Tasks
1. **Environment Setup**:
   - Build the game world:
     - Create the ninja continent with at least 3 villages, 2 training zones, and 1 neutral battlefield.
     - Implement a simple map system with grid-based navigation.

2. **Character Creation**:
   - Add clan selection during character creation.
   - Implement natural chakra releases (Fire, Water, Earth, Lightning, Wind).
   - Allow stat customization (Dexterity, Strength, CIS, etc.).

3. **Combat System**:
   - Implement the **grid-based combat mechanics**:
     - Movement rules based on speed stats.
     - Stance mechanics (Offensive, Defensive, Balanced).
     - Hitroll, damroll, and automated basic attacks.
   - Add timer-based jutsu casting with cooldowns and proficiency scaling.
   - Test elemental interactions (Fire > Wind, etc.).

4. **Progression System**:
   - Introduce grindy and non-grindy training mechanics.
   - Add basic questlines to reward progression milestones.

5. **Basic NPC AI**:
   - Implement AI for training dummies and basic enemy ninjas.

---

## Phase 2: Ninja Continent Expansion and Features
### Objectives
- Expand the ninja gameplay experience with more locations, NPCs, and training opportunities.
- Flesh out clan-specific abilities and advanced combat features.

### Key Tasks
1. **World Expansion**:
   - Add new zones (e.g., forests, mountains) with unique environmental effects (e.g., reduced movement in dense forests).
   - Implement advanced terrain effects (e.g., high ground for ranged bonuses).

2. **Clan-Specific Features**:
   - Develop unique clan abilities:
     - Passive bonuses (e.g., faster chakra regen for Clan A).
     - Signature jutsus (e.g., fire-based AoE for Clan B).
   - Add clan-specific questlines for progression.

3. **Advanced Combat Features**:
   - Add mid-range and long-range weapons (kunai, shuriken, short bows).
   - Introduce more status effects (e.g., Chakra Burn, Fatigue, Stun).

4. **NPC Interactions**:
   - Add recruitable NPCs for group missions.
   - Introduce roaming NPC enemies with basic patrol AI.

---

## Phase 3: Samurai Expansion
### Objectives
- Introduce the samurai continent, a new class, and inter-faction conflicts.
- Add new combat mechanics, focusing on melee dominance and territory control.

### Key Tasks
1. **Samurai Gameplay**:
   - Implement kenjutsu styles with melee-focused stances and abilities:
     - **Slash Zone**: Attack all adjacent squares.
     - **Blade Dash**: Close the gap and strike in one turn.
   - Add bow/crossbow weapons for mid-range versatility.

2. **Territory Control**:
   - Allow players to conquer neutral and enemy zones.
   - Add simple RTS mechanics for resource gathering and basic defenses.

3. **World Expansion**:
   - Add the samurai continent with new villages, castles, and training zones.

4. **Faction Mechanics**:
   - Introduce faction-based questlines and rewards.
   - Enable basic faction rivalries (e.g., Ninja vs Samurai skirmishes).

---

## Phase 4: Advanced Combat and Wizardry Expansion
### Objectives
- Add magic classes with unique combat styles and resources (e.g., mana).
- Introduce advanced elemental interactions and world effects.

### Key Tasks
1. **Magic System**:
   - Implement spellcasting mechanics:
     - Fire, Frost, Arcane, Necromancy, and Holy magic types.
     - Add mana management and spell cooldowns.
   - Develop magic interactions with the environment (e.g., fire stronger in dry zones).

2. **Anti-Magic Classes**:
   - Create counter-classes with abilities to silence or disrupt spellcasters.

3. **World Expansion**:
   - Add the magical realm continent with leyline-based resources.
   - Include magical towers and guilds for questlines.

---

## Phase 5: RTS Leadership Mechanics
### Objectives
- Add RTS-style gameplay for leaders to manage territories, recruit troops, and engage in large-scale battles.

### Key Tasks
1. **Resource Management**:
   - Implement income, resource gathering, and resource allocation systems.
   - Allow leaders to build structures (e.g., headquarters, defenses).

2. **Troop Training**:
   - Add recruitable units and training mechanics.
   - Introduce unit upgrades based on faction abilities.

3. **Large-Scale Battles**:
   - Enable leaders to organize and execute faction wars.
   - Add mechanics for troop deployment and strategic abilities.

---

## Phase 6: Supernatural Expansion
### Objectives
- Introduce supernatural themes with new races and planar combat.

### Key Tasks
1. **Playable Races**:
   - Add Vampires and Werewolves with unique abilities and weaknesses.
   - Develop transformation mechanics (e.g., lycanthropy triggers).

2. **Planar Realms**:
   - Add Heaven, Hell, and Limbo as explorable regions.
   - Implement Angels and Demons as factions with unique questlines.

3. **Supernatural Combat**:
   - Introduce celestial and infernal resource mechanics.
   - Allow players to build planar fortresses and summon special units.

---

## Phase 7: Long-Term Systems and QoL Features
### Objectives
- Refine existing systems, add quality-of-life features, and enable large-scale player interactions.

### Key Tasks
1. **Guilds and Clans**:
   - Add player-created guilds with shared resources and goals.
   - Enable guild-based territory wars.

2. **Crafting System**:
   - Allow players to craft weapons, armor, and consumables.
   - Introduce rare materials from quests or zones.

3. **Dynamic Events**:
   - Add world events like invasions, planar rifts, and seasonal challenges.

4. **Performance Optimization**:
   - Ensure smooth gameplay for large-scale battles and RTS mechanics.

---

## Next Steps (Immediate Focus)
1. **Build Core Ninja Framework**:
   - Finalize grid-based combat, basic NPC AI, and elemental interactions.
   - Test proficiency-based jutsu mechanics.
2. **Create Initial World**:
   - Design 3 core villages and training zones for the ninja continent.
   - Add environmental effects to the map.
3. **Iterate on Character Creation**:
   - Implement clan selection and stat customization.
   - Add a basic questline to introduce progression mechanics.

---

## Summary
This development route provides a clear path to building a scalable and feature-rich MUD. By focusing on **core mechanics first** and layering expansions iteratively, Shinobi MUD will evolve into a dynamic and engaging experience for players at every level.

