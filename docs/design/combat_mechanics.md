# Combat Mechanics

## Summary

Veilborn MUD combat is built around automatic baseline fighting plus player-selected combat choices. The current implementation uses round combat: a player engages a hostile NPC, the server resolves due action rounds, and any queued stance or technique modifiers are applied during that round.

Dexterity and Agility determine how many combat rounds a character receives per second. A normal auto attack consumes one round, and active combat choices such as techniques consume that round instead of resolving outside the main action rhythm.

This file explains the live system and marks the remaining follow-up work for skills and expressions.

## Current Combat Loop

Combat starts with `attack <character>`. The command engages a hostile NPC at the player's current grid position and stores that engagement. Once engaged, the recurring combat tick checks whether the player's next combat round is due.

The current base round speed is derived from Dexterity and Agility. Each character starts at 1 attack per second and can scale to 5 attacks per second at 100 Dexterity and 100 Agility. On each due round, the system checks range, resolves the player's outgoing action if possible, then resolves the NPC counterattack when the NPC is close enough.

If the target is out of range, the round is rescheduled and the queued action remains pending. This matters for techniques because a player should not lose a prepared action simply because the target moved or the player is not currently adjacent.

Current round resolution includes:

- Player hit chance from Dexterity, stance accuracy, and queued accuracy against NPC Agility plus evasion bonuses.
- Player damage from Strength, equipped weapon damage, stance damage, and queued damage.
- NPC hit chance from NPC Dexterity plus accuracy bonuses against player Agility, stance evasion, and queued evasion.
- NPC technique use when the NPC has authored `combat_techniques` and enough stamina.
- Incoming damage reduction from stance reduction and queued reduction.
- Fatigue gain when a valid in-range round resolves.
- Substitution expression consumption when it prevents a hostile hit.
- Engagement cleanup when an NPC is defeated, the target disappears, the player disconnects, or the player is defeated.

Player defeat currently restores the player to full health at the same grid coordinate and clears the engagement. NPC defeat marks the NPC defeated and clears the engagement.

## Attributes

Strength is the baseline damage attribute. A normal player attack uses roughly half Strength as its base before equipment, stance, and queued action modifiers are added. NPCs use the same Strength baseline, plus any authored damage bonus.

Dexterity improves outgoing hit chance and contributes to combat speed.

Agility improves evasion against incoming attacks and contributes to combat speed.

Stamina powers physical combat techniques. Technique stamina is spent when the technique is queued, not when the pulse resolves.

Wisp powers expressions. Current expressions keep their own activation and state behavior; future combat work should bring expression timing into the shared combat-round economy.

NPCs have the same core sheet shape as players: health, stamina, wisp, Strength, Dexterity, Agility, Intelligence, and Wisdom. Builder-created NPCs default those values to 10.

## Stances

Stances are persistent posture choices. They are not one-shot actions. A stance stays active until changed or cleared, and it modifies the character's ordinary combat profile.

Current stance fields can affect:

- Accuracy
- Evasion
- Damage
- Incoming damage reduction
- Round cadence through the legacy `pulse_seconds` multiplier

The current placeholder stance set is S1 through S5:

- S1 favors accuracy.
- S2 favors damage.
- S3 is balanced.
- S4 favors evasion.
- S5 favors damage reduction.

Stances remain persistent posture modifiers. They may adjust round cadence, accuracy, damage, defense, or resource pressure, but they should not replace techniques, skills, or expressions as active round-consuming choices.

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

A technique consumes the character's action for one combat round unless authored otherwise. For example, a kick technique takes the place of the normal auto attack for that round, applying its own accuracy, damage, movement, or defense rules.

## Skills and Expressions

Skills and expressions should eventually use the same round economy as techniques.

Combat skills are active martial actions. They should be treated as round-based augments or replacements for a normal auto attack. A punch, kick, weapon form, grapple, or dodge skill can consume the next available round and apply its authored effects.

Expressions are wisp-based actions. Some expressions should resolve in one round. Stronger or more complex expressions may require multiple rounds to prepare before they resolve. Multi-round expressions should occupy the character's combat action during their preparation time so they cannot freely stack with normal attacks.

The long-term rule is simple: if the player is doing something meaningful in combat, it should use combat rounds. Auto-attacks fill empty rounds, while techniques, skills, and expressions replace or augment those rounds.

## Round Speed

The combat model starts at 1 attack per second and scales to 5 attacks per second when both Dexterity and Agility are fully upgraded to 100.

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

Under this system, "round" means one available action slot. A character at 1 attack per second receives one action slot per second. A character at 5 attacks per second receives five action slots per second. Empty slots perform normal auto attacks. Queued techniques, active combat skills, or expressions consume one or more slots according to their authored action cost.

## Implementation Notes

The Dex/Agi round-speed system is implemented for player engagement rounds. The live code still keeps legacy `pulse_seconds` and `next_pulse_at` fields for compatibility with older saves, tests, and stance content, but precise scheduling uses `next_round_at`.

Future implementation should preserve the useful parts of the current system:

- Persistent engagements.
- Transaction-safe combat ticks.
- Grid range checks.
- Stance modifiers.
- One-shot queued action modifiers.
- Resource costs paid when an action is committed.
- Queued actions remaining pending when range prevents resolution.

The main future change is routing combat skills and expressions through the same action-slot system so combat stays automatic, readable, and fair.
