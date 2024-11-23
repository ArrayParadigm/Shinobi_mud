# TODO: Shinobi MUD Development Roadmap

## Overview
This document outlines the key tasks and features required for the development of Shinobi MUD, incorporating existing mechanics from the grid-based combat system, RTS expansion, and long-term vision. Tasks are categorized and prioritized for efficient development.

---

## Core Development Phases

### **Phase 1: Core Ninja Gameplay**
**Objective**: Establish the foundation of Shinobi MUD with grid-based combat, clan mechanics, and chakra-driven abilities.

#### **Key Features**:
1. **Character Creation**:
   - Implement clan selection during character creation, with each clan granting:
     - Natural chakra releases (e.g., Fire, Water, Earth, Lightning, Wind).
     - Unique passive abilities and signature jutsus.
   - Allow for initial stat allocation (e.g., Dexterity, Chakra Control).

2. **Combat System**:
   - Finalize the **grid-based combat system**:
     - Movement mechanics (e.g., speed-based distance).
     - Stance-based modifiers (Offensive, Defensive, Balanced).
     - Proficiency-based jutsu execution (Dex + CIS + LJ + HSP).
   - Implement **rock-paper-scissors elemental interactions** for jutsus:
     - Fire > Wind, Wind > Lightning, etc.
   - Add timers and cooldowns for special abilities.

3. **Training and Progression**:
   - Add grindy and non-grindy training systems:
     - Manual repetition for grindy players.
     - Quest-based or milestone progression for non-grindy players.
   - Allow stat customization through training (e.g., chakra control improves CIS).

4. **Core World Design**:
   - Design the initial ninja continent with key territories:
     - Villages, training grounds, neutral zones, and enemy bases.
   - Implement terrain effects (e.g., high ground, cover mechanics).

5. **Basic NPC Interactions**:
   - Add recruitable NPCs for training missions.
   - Introduce simple enemy AI with elemental counters and grid awareness.

---

### **Phase 2: Samurai Expansion**
**Objective**: Add a new continent featuring samurai gameplay, with distinct mechanics and a focus on melee combat.

#### **Key Features**:
1. **Samurai Mechanics**:
   - Introduce **Kenjutsu styles**:
     - Focus on melee combat with powerful sword techniques.
     - Add samurai-specific stances (e.g., Bushido Honor for defense, Ronin Fury for attack speed).
   - Implement abilities like:
     - **Slash Zone**: Attack all adjacent squares.
     - **Blade Dash**: Move and attack simultaneously.
   - Add bow and crossbow weapons for ranged combat.

2. **Territory Control**:
   - Add a new region with conquerable samurai castles and villages.
   - Enable faction-based conflicts between ninjas and samurai.

3. **Worldbuilding**:
   - Expand the map to include the samurai continent with unique terrain and cultural elements.

---

### **Phase 3: Wizardry Expansion**
**Objective**: Introduce wizards and anti-magic classes, adding magic-based combat and advanced elemental interactions.

#### **Key Features**:
1. **Magic System**:
   - Add spellcasting mechanics:
     - Fire, Frost, Arcane, Necromancy, and Holy magic affinities.
     - Spell interactions based on terrain and weather (e.g., Frost stronger in snow).
   - Add mana management mechanics (e.g., spell cooldowns, regeneration).

2. **Anti-Magic Mechanics**:
   - Introduce a counter-class specializing in disrupting spells (e.g., silencing zones, mana drain).

3. **World Expansion**:
   - Add the magical realm continent with leyline-based resource management.
   - Include magic towers and guilds for wizard factions.

---

### **Phase 4: RTS Leadership Mechanics**
**Objective**: Add RTS-style gameplay for players who achieve leadership roles in their factions.

#### **Key Features**:
1. **Territory Management**:
   - Introduce resource management:
     - Income (via taxes, trade).
     - Materials (wood, stone, metal).
     - Special resources (chakra crystals, magical essence).
   - Add buildable structures:
     - Headquarters, training grounds, defenses.
     - Faction-specific buildings (e.g., Ninja Spy Networks, Samurai Dojos).

2. **Troop Recruitment and Training**:
   - Allow leaders to recruit and train warriors:
     - Ninja specialists, samurai generals, mage troops.
   - Introduce troop upgrades based on leader’s resources and faction abilities.

3. **Faction Rivalries**:
   - Add inter-faction diplomacy:
     - Alliances, trade, sabotage, and wars.

4. **Large-Scale Combat**:
   - Enable leaders to organize large-scale battles across territories.

---

### **Phase 5: Supernatural Expansion**
**Objective**: Introduce new playable races and planar combat with supernatural themes.

#### **Key Features**:
1. **New Races**:
   - Vampires: Stealthy and blood-based abilities.
   - Werewolves: Strong melee fighters with transformation mechanics.
2. **Planar Realms**:
   - Add Heaven, Hell, and Limbo as accessible regions.
   - Introduce Angels and Demons as playable factions or NPC enemies.
3. **Supernatural Mechanics**:
   - Include celestial and infernal resource management.
   - Allow players to build planar fortresses and summon unique troops.

---

## Immediate TODO List

### **High Priority**:
1. Finalize the **grid-based combat system** and test movement, stances, and jutsu timers.
2. Implement clan selection during character creation with basic chakra affinities.
3. Add core ninja abilities and elemental interactions.
4. Build the ninja continent with at least 3 villages, training grounds, and neutral zones.
5. Develop basic NPC AI for training and combat scenarios.

### **Medium Priority**:
1. Expand training systems to include grindy and non-grindy paths.
2. Begin designing the samurai mechanics and territory control features.
3. Add a resource management prototype for future RTS integration.

### **Low Priority**:
1. Plan the wizardry and supernatural expansions.
2. Draft advanced AI for large-scale battles.
3. Design faction diplomacy and alliance mechanics.

---

## Summary

This roadmap provides a structured approach to developing Shinobi MUD, focusing on:
1. **Core ninja gameplay** and grid-based combat mechanics.
2. **Phased expansions** to introduce new classes, continents, and gameplay layers.
3. **RTS leadership systems** for endgame strategy and progression.
4. **Supernatural themes** for future expansions.

By following this roadmap, Shinobi MUD will evolve into a rich, immersive world with diverse gameplay for all players.

