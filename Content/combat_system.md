# Shinobi MUD Real-Time Combat System Overview

## Core Combat Features

### 1. Real-Time Combat
- **Automated normal combat**: Hitrolls and damrolls are calculated in real-time, based on player stats like Strength, Dexterity, and stances.
- Players can dynamically switch **stances** and **styles** to counter opponents or adjust their strategy mid-combat.

### 2. Timer-Based Jutsus and Abilities
- **Special skills** (like jutsus, spells, or abilities) are timer-based:
  - Players begin **preparing** abilities with a **cast time** and execute them after the timer ends.
  - Offensive moves typically have **longer cast times** than defensive moves, allowing for counters.
- **Cooldowns** are applied to prevent ability spamming and to encourage strategic use of abilities.

### 3. Defensive Priority
- Defensive moves are **faster to execute** than offensive ones, enabling **reactionary play**:
  - Example: A defensive **Water Wall** jutsu might execute faster than an offensive **Fireball**, mitigating or nullifying the attack.

---

## Proficiency System

Proficiency determines the **speed and efficiency** of jutsus and abilities. It is calculated using multiple attributes:


### Proficiency Factors:
1. **Dexterity (Dex)**: Influences overall speed and reaction time in combat.
2. **Chakra Infused Speed (CIS)**: Measures how efficiently the character channels chakra to boost their speed.
3. **Lightning Jutsu (LJ)**: Specialized stat that affects the speed of lightning-based abilities.
4. **Hand Sign Proficiency (HSP)**: Affects how quickly and efficiently the player can perform hand signs to activate jutsus.

**Proficiency Effects:**
- Shorter **casting times** for jutsus.
- Reduced **cooldowns** for abilities.
- Faster stance-switching and reactionary actions.

---

## Stances and Styles

### 1. Stances
Players can dynamically switch stances during combat, which affects their offense, defense, and reaction times:
- **Offensive Stance**:
  - Increases hitroll and damroll.
  - Decreases defense and reaction speed.
- **Defensive Stance**:
  - Increases defense and reaction speed.
  - Decreases offensive capability.
- **Balanced Stance**:
  - Neutral stance with no major bonuses or penalties.
  - Ideal for transitioning between offensive and defensive strategies.

### 2. Styles
Styles represent specialized combat techniques that synergize with jutsus:
- **Taijutsu**: Focuses on physical combat and melee damage.
- **Ninjutsu**: Specializes in elemental attacks like Fireball or Water Wall.
- **Genjutsu**: Focuses on illusions and debuffs, affecting the opponent’s ability to act effectively.

---

## Elemental Interactions

Elemental jutsus follow a **rock-paper-scissors** dynamic:
- **Fire beats Wind** (Fire consumes Wind).
- **Wind beats Lightning** (Wind disrupts Lightning).
- **Lightning beats Water** (Electricity flows through Water).
- **Water beats Fire** (Water douses Fire).
- **Earth beats Lightning** (Earth grounds Lightning).

**Dual-Element Jutsus:**
- Advanced characters can combine elements to create unique jutsus (e.g., Fire + Wind = Firestorm).
- Dual-element attacks can be countered only partially by single-element defenses.

---

## Combat Flow Example

1. **Player 1** prepares **Fireball Jutsu**.
   - Cast time: 3 seconds (adjusted by Proficiency).
2. **Player 2** reacts with **Water Wall**.
   - Cast time: 2 seconds (faster due to being defensive).
3. **Resolution**:
   - If **Water Wall** executes first, it mitigates or nullifies Fireball's damage.
   - If Fireball executes first, some damage might pass through, depending on timing and counters.

---

## Advanced Mechanics

### 1. Dynamic Combat Logs
Combat logs provide feedback for strategic adjustments:


### 2. Mastery Levels for Jutsus
- Jutsus gain **Mastery Levels** through use or training.
- Higher mastery unlocks:
  - Faster casting times.
  - Reduced cooldowns.
  - Enhanced effects (e.g., Fireball gains an explosive radius at Mastery Level 3).

### 3. Chakra Zones
Introduce battlefield zones that affect chakra use:
- **High Chakra Zone**: Amplifies chakra-based attacks.
- **Low Chakra Zone**: Reduces the effectiveness of jutsus.

### 4. Status Effects
- **Chakra Burn**: Reduces Chakra Infused Speed (CIS) after overusing abilities.
- **Exhaustion**: Lowers Dexterity after prolonged combat.
- **Disrupted Focus**: Reduces Hand Sign Proficiency (HSP) due to debuffs or interruptions.

---

## Summary

This combat system emphasizes **strategic depth** through:
1. **Real-time execution** of normal combat.
2. **Timer-based special abilities** with casting delays and cooldowns.
3. **Dynamic counters and reactions** influenced by stances and styles.
4. **Proficiency-based scaling** for jutsus and abilities.
5. **Rock-paper-scissors elemental interactions**, with potential for dual-element combinations.

This design ensures fast-paced, engaging combat with opportunities for tactical decision-making and skillful play.
