# Combat Mechanics

## Summary

Shinobi MUD combat is built around automatic baseline fighting plus player-selected combat choices. The current implementation uses slower pulse combat: a player engages a hostile NPC, the server resolves due pulses, and any queued stance or technique modifiers are applied during that pulse.

The intended direction is a faster round-based combat loop. In that model, Dexterity and Agility determine how many combat rounds a character receives per second. A normal auto attack consumes one round, and active combat choices such as techniques, skills, and jutsus consume one or more rounds instead of resolving outside the main action rhythm.

This file separates current behavior from intended direction so future combat work can build from the live system without losing the target design.

## Current Combat Loop

Combat starts with `attack <character>`. The command engages a hostile NPC at the player's current grid position and stores that engagement. Once engaged, the recurring combat tick checks whether the player's next combat pulse is due.

The current base pulse speed is 6 seconds. Stances can override that pulse timing through their authored `pulse_seconds` value. On each due pulse, the system checks range, resolves the player's outgoing action if possible, then resolves the NPC counterattack when the NPC is close enough.

If the target is out of range, the pulse is rescheduled and the queued action remains pending. This matters for techniques because a player should not lose a prepared action simply because the target moved or the player is not currently adjacent.

Current pulse resolution includes:

- Player hit chance from Dexterity, stance accuracy, and queued accuracy against NPC evasion.
- Player damage from Strength, equipped weapon damage, stance damage, and queued damage.
- NPC hit chance from NPC accuracy against player Agility, stance evasion, and queued evasion.
- Incoming damage reduction from stance reduction and queued reduction.
- Fatigue gain when a valid in-range pulse resolves.
- Substitution jutsu consumption when it prevents a hostile hit.
- Engagement cleanup when an NPC is defeated, the target disappears, the player disconnects, or the player is defeated.

Player defeat currently restores the player to full health at the same grid coordinate and clears the engagement. NPC defeat marks the NPC defeated and clears the engagement.

## Attributes

Strength is the current baseline damage attribute. A normal player attack uses roughly half Strength as its base before equipment, stance, and queued action modifiers are added.

Dexterity currently improves outgoing hit chance. In the intended round model, Dexterity also contributes to combat speed.

Agility currently improves evasion against incoming attacks. In the intended round model, Agility also contributes to combat speed.

Stamina powers physical combat techniques. Technique stamina is spent when the technique is queued, not when the pulse resolves.

Chakra powers jutsus. Current jutsus keep their own activation and state behavior, but future combat work should bring jutsu timing into the shared combat-round economy.

## Stances

Stances are persistent posture choices. They are not one-shot actions. A stance stays active until changed or cleared, and it modifies the character's ordinary combat profile.

Current stance fields can affect:

- Accuracy
- Evasion
- Damage
- Incoming damage reduction
- Pulse speed

The current placeholder stance set is S1 through S5:

- S1 favors accuracy.
- S2 favors damage.
- S3 is balanced.
- S4 favors evasion.
- S5 favors damage reduction.

In the intended combat model, stances should remain persistent posture modifiers. They may adjust round cadence, accuracy, damage, defense, or resource pressure, but they should not replace techniques, skills, or jutsus as active round-consuming choices.

## Techniques

Techniques are stamina-based active combat choices. The canonical command is `technique <name>`, with direct command wrappers for common techniques such as `strike`, `guard`, `feint`, and `recover`.

Current technique rules:

- Techniques require an active combat engagement.
- Only one technique can be queued at a time.
- Queueing a new technique replaces the previous queued technique.
- Stamina is spent immediately when the technique is queued.
- If the target is out of range, the queued technique remains pending.
- Techniques do not currently add progression.

Current first-pass techniques:

- `strike`: costs 2 stamina and adds damage to the next eligible outgoing attack.
- `guard`: costs 2 stamina, skips the outgoing attack, improves evasion, and reduces incoming damage for that pulse.
- `feint`: costs 3 stamina and adds accuracy plus a small damage bonus.
- `recover`: costs 0 stamina, skips the outgoing attack, and restores stamina up to maximum stamina.

In the intended round model, a technique consumes the character's action for one combat round unless authored otherwise. For example, a kick technique would take the place of the normal auto attack for that round, applying its own accuracy, damage, movement, or defense rules.

## Skills and Jutsus

Skills and jutsus should eventually use the same round economy as techniques.

Combat skills are active martial actions. They should be treated as round-based augments or replacements for a normal auto attack. A punch, kick, weapon form, grapple, or dodge skill can consume the next available round and apply its authored effects.

Jutsus are chakra-based actions. Some jutsus should resolve in one round. Stronger or more complex jutsus may require multiple rounds to prepare before they resolve. Multi-round jutsus should occupy the character's combat action during their preparation time so they cannot freely stack with normal attacks.

The long-term rule is simple: if the player is doing something meaningful in combat, it should use combat rounds. Auto-attacks fill empty rounds, while techniques, skills, and jutsus replace or augment those rounds.

## Intended Round Speed

The target combat model starts at 1 attack per second and scales to 5 attacks per second when both Dexterity and Agility are fully upgraded to 100.

Use the average of Dexterity and Agility:

```text
speed_stat = (dexterity + agility) / 2
attacks_per_second = 1 + 4 * speed_stat / 100
```

The result should be capped from 1 to 5 attacks per second:

```text
attacks_per_second = min(5, max(1, attacks_per_second))
```

Examples:

| Dexterity | Agility | Average | Attacks/sec | Round length |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 1.0 | 1.00s |
| 10 | 10 | 10 | 1.4 | 0.71s |
| 25 | 25 | 25 | 2.0 | 0.50s |
| 50 | 50 | 50 | 3.0 | 0.33s |
| 75 | 75 | 75 | 4.0 | 0.25s |
| 100 | 100 | 100 | 5.0 | 0.20s |

Under this system, "round" means one available action slot. A character at 1 attack per second receives one action slot per second. A character at 5 attacks per second receives five action slots per second. Empty slots perform normal auto attacks. Queued techniques, active combat skills, or jutsus consume one or more slots according to their authored action cost.

## Implementation Notes

The Dex/Agi round-speed system is intended design, not fully implemented yet. The live code still uses pulse combat with a current base of 6 seconds.

Future implementation should preserve the useful parts of the current system:

- Persistent engagements.
- Transaction-safe combat ticks.
- Grid range checks.
- Stance modifiers.
- One-shot queued action modifiers.
- Resource costs paid when an action is committed.
- Queued actions remaining pending when range prevents resolution.

The main future change is replacing slow pulse timing with round generation derived from Dexterity and Agility. Once that exists, techniques, combat skills, and jutsus should all route through the same action-slot system so combat stays automatic, readable, and fair.
