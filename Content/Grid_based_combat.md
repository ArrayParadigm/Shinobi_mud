# Shinobi MUD Grid-Based Combat System Overview

## Core Combat Features

### 1. Dynamic Movement and Positioning
Players and NPCs can move around a **grid-based map**, making positioning a critical part of combat strategy:
- **Ranged combatants** (e.g., bow users, throwing weapons, ninjutsu specialists) can stay at a distance to maximize their effectiveness.
- **Taijutsu users** (hand-to-hand combat) and **kenjutsu users** (swords) will focus on **closing the gap** to deal damage up close.
- Movement around the grid allows players to:
  - **Evade attacks** by moving out of an opponent's range.
  - **Flank enemies** to gain tactical advantages.
  - **Control space** by positioning defensively to block routes or force opponents into choke points.

### 2. Range Categories for Attacks
To incorporate **ranged vs melee mechanics**, each attack or jutsu can have an **optimal range**:
- **Melee Range (1 square)**:
  - Taijutsu, Kenjutsu, and close-range abilities like **Chidori** or **Shadow Clone Jutsu**.
- **Mid-Range (2-4 squares)**:
  - Ninjutsu and moderate-range weapons like **kunai**, **shuriken**, or **short bows**.
- **Long-Range (5+ squares)**:
  - Long-range ninjutsu (e.g., **Fireball Jutsu**, **Water Dragon Jutsu**) and weapons like **longbows** or **crossbows**.
- **Cross-Range Specialties**:
  - Some abilities, like certain Genjutsu or elemental AOE (Area of Effect) abilities, can affect multiple ranges or grid spaces.

**Strategic Movement Example:**
- A **Taijutsu user** attempts to close the gap to reach melee range.
- A **ranged ninjutsu user** moves away to maintain optimal distance while preparing a mid-range or long-range attack.
- A **kenjutsu user** uses a **dash ability** to close the gap and lock the ninjutsu user into melee combat.

---

## Terrain and Obstacles
The grid system can include **terrain effects** and **obstacles** to make combat more tactical:
- **Cover**: Obstacles like trees, rocks, or walls can block line-of-sight for ranged attacks, forcing players to reposition.
- **Elevation**: High ground could give ranged combatants an advantage (e.g., increased range or accuracy).
- **Hazards**: Lava pits, water zones, or other hazardous areas could deal damage or restrict movement.
- **Chakra Zones**: High chakra areas could boost ninjutsu power, while low chakra areas might reduce ability effectiveness.

**Example:**
- A **Taijutsu user** hides behind a rock to avoid being targeted by a **Fireball Jutsu**.
- A **ninjutsu user** takes high ground to increase their range and gain a damage boost.

---

## Movement and Action Economy
Each turn, players can spend their **Action Points (AP)** or **Stamina** to perform the following:
1. **Move**: Move a set number of spaces on the grid, based on speed or Dexterity.
2. **Attack**: Perform a basic attack (hitroll and damroll apply).
3. **Prepare Jutsu**: Begin preparing a special ability, which may require multiple turns.
4. **Defend**: Take a defensive stance, increasing evasion or reducing incoming damage.
5. **Switch Stance**: Change to Offensive, Defensive, or Balanced stance.
6. **Interact**: Throw kunai, pick up an item, or trigger a trap.

**Movement Mechanics:**
- **Speed Stat**: Determines how far a player can move per turn (e.g., 3 squares by default, +1 per 5 Dexterity points).
- **Chakra Dash**: Consumes chakra to quickly close gaps (e.g., Taijutsu specialists could dash 5 squares instantly).
- **Stealth Movement**: Characters skilled in stealth could move undetected for a certain number of squares.

---

## Class-Specific Perks for the Grid System

### Taijutsu (Close Combat Specialists)
- **Strengths**:
  - Can close the gap quickly with **Chakra Dash** or **Leap** abilities.
  - Strong damage and accuracy at melee range.
- **Weaknesses**:
  - Vulnerable to kiting (being kept at a distance by ranged enemies).
- **Grid-Specific Abilities**:
  - **Grapple**: Lock an enemy in melee range, preventing them from moving for 1-2 turns.
  - **Dash**: Instantly move 3-5 squares to close the gap.

### Kenjutsu (Sword Fighters)
- **Strengths**:
  - High melee damage and access to mid-range slashes (e.g., crescent slash or sword beams).
  - Can combine speed with high burst damage.
- **Weaknesses**:
  - Relies on maintaining melee range, similar to Taijutsu.
- **Grid-Specific Abilities**:
  - **Slash Zone**: Attack all adjacent squares in one move.
  - **Blade Dash**: Move 2-3 squares and attack in the same turn.

### Ninjutsu (Ranged Specialists)
- **Strengths**:
  - Effective at mid and long range with strong elemental attacks.
  - Can exploit weaknesses in elemental counters.
- **Weaknesses**:
  - Weaker at close range; needs to maintain distance.
- **Grid-Specific Abilities**:
  - **Wall Creation**: Create a temporary obstacle to block movement or line-of-sight.
  - **AOE Attacks**: Affect multiple squares at once with jutsus like **Fireball** or **Water Dragon**.

### Genjutsu (Illusion and Debuff Specialists)
- **Strengths**:
  - Disrupts opponents by reducing stats or immobilizing them.
  - Can force opponents to waste movement or actions.
- **Weaknesses**:
  - Lower direct damage output; relies on teammates or drawn-out fights.
- **Grid-Specific Abilities**:
  - **Illusion Field**: Target a 3x3 grid area, reducing accuracy and defense of enemies within.
  - **Mind Lock**: Immobilize an enemy for 1-2 turns.

### Ranged Weapons (Kunai, Shuriken, Bows)
- **Strengths**:
  - Quick attacks that can target multiple ranges.
  - Useful for maintaining pressure on opponents.
- **Weaknesses**:
  - Weaker damage compared to jutsus or melee.
- **Grid-Specific Abilities**:
  - **Ricochet**: Target multiple enemies in a straight line.
  - **Piercing Shot**: Ignore cover bonuses for one attack.

---

## Advanced Mechanics

### Stealth and Ambush
- **Stealth**: Characters can enter a stealth mode, hiding from enemies unless detected by high Perception or certain jutsus.
- **Ambush**: Attacking from stealth grants bonuses to hitroll and damroll.

### Traps and Tools
- Players can deploy traps (e.g., explosive tags) or use tools like smoke bombs to manipulate the battlefield.

### Environment Effects
- Weather and terrain could influence combat:
  - Rain boosts **Water Jutsu** but weakens **Fire Jutsu**.
  - Muddy terrain slows movement.

---

## Summary
This grid-based system adds depth to combat by focusing on:
1. **Dynamic positioning**: Encourages players to move strategically, exploiting ranges and terrain.
2. **Class synergy**: Differentiates combat styles with unique perks and abilities.
3. **Tactical flexibility**: Stances, movement options, and terrain effects make each battle unique.
4. **Real-time depth**: Combines the thrill of real-time combat with the strategy of turn-based systems.

This approach is perfect for a ninja-based MUD, creating an immersive and strategic gameplay experience.
