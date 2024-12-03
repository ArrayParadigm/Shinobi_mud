# Shinobi_MUD Project Plan

## **Refined Vision Statement**
**"Shinobi_MUD is a hybrid sandbox MUD designed to provide an immersive experience of exploration, skill-based combat, and player-driven storytelling, with dynamic zones and a balance of automated and manual interactions. Players will train, fight, and shape the world around them while engaging in roleplay quests, PVP battles, and community-building activities. The game combines traditional MUD mechanics with innovative systems for dynamic battlefields, RTS elements, and a persistent, evolving world."**

---

## **Key Areas of Focus**

### **1. Map and Zone System**
- **Hybrid Map**: ASCII-based wilderness maps with overlays for detailed zones (cities, dungeons).
- **Room/Zone Definitions**: Include room descriptions, exits, items, NPCs, and environmental effects.
- **Dynamic Integration**: Allow players to influence parts of the map (e.g., building towns or roads).

### **2. Player Mechanics**
- **Skill-Based Progression**: Use-based skill growth (e.g., combat, crafting, stealth).
- **Freedom in Building**: Areas where players can construct or expand infrastructure.
- **Core Attributes**: Health, stamina, chakra, honor, mana, and class-specific stats.

### **3. Combat System**
- **Skill-Based Combat with RTS Influence**:
  - Automated base combat (like traditional MUDs).
  - Active skill usage layered on top (player-initiated commands for abilities).
  - Eventual RTS-style battlefield management and city sieges.

### **4. Roleplay and Interaction**
- **Command-Driven Interaction**: Core mechanic for players to explore, build, and communicate.
- **NPC Behaviors**: Long-term goal of AI-driven NPCs with schedules, missions, and reactions to player actions.

### **5. Technical Goals**
- **Modular Architecture**: Clean, reusable code for map, combat, and player systems.
- **Alpha State Goal**: Prioritize expanding functionality to reach a playable prototype.
- **Scalable Systems**: Design for 100+ users but optimized for smaller player bases initially.

---

## **Proposed Project Plan**

### **Phase 1: Establish Core Systems (Alpha Stage)**

#### **1. Map and Zones**
- Simplify the grid-based world map with ASCII wilderness.
- Overlay modular zones on the map (e.g., cities, dungeons).
- Implement basic room definitions: descriptions, exits, and placeholders for items/NPCs.

#### **2. Player Basics**
- Create a character system with health, stamina, and chakra.
- Implement basic movement between rooms and zones.
- Add commands for viewing stats, room descriptions, and map visibility.

#### **3. Combat Prototype**
- Implement automated combat (hitrolls, damrolls).
- Add a simple command for active abilities (e.g., `/fireball` reduces stamina/chakra).
- Include a basic PVP mode for testing.

#### **4. Admin and Debug Tools**
- Build commands for creating/editing zones and rooms (e.g., `/dig`, `/createzone`).
- Logging for player actions and server events.

---

### **Phase 2: Expand Gameplay Features**

#### **1. Skill Progression**
- Introduce use-based skill growth for combat and general activities.
- Add systems for crafting, gathering, and stealth.

#### **2. Dynamic World**
- Enable areas where players can construct buildings or alter the environment.
- Add commands for manipulating these areas (e.g., `/build`, `/terraform`).

#### **3. Expanded Combat**
- Add a cooldown system for abilities.
- Introduce elemental interactions (e.g., fire counters wind, water beats fire).
- Begin laying groundwork for RTS mechanics (e.g., controlling NPC squads).

#### **4. Roleplay Enhancements**
- Create NPCs with basic behaviors and quests.
- Add commands for emotes and other roleplay tools.

---

### **Phase 3: Long-Term Features**

#### **1. RTS and City Management**
- Introduce mechanics for armies, resource collection, and city building.
- Add zones that represent larger regions for player governance.

#### **2. AI-Driven NPCs**
- Expand NPC behaviors to include schedules and dynamic interactions with players.

#### **3. Advanced Roleplay Tools**
- Add systems for live events and custom quests.
- Implement tools for admins to create story arcs dynamically.

---

## **Next Steps**

### **1. Code Review and Cleanup**
- Analyze each module in your current codebase and align it with the project plan.
- Focus first on the map/zone system and player movement.

### **2. Implementation Framework**
- Develop a modular structure for the core systems (map, zones, players, and combat).
- Ensure logging and debugging tools are in place for smoother development.

### **3. Prototype Milestones**
- Set up incremental goals to test each feature (e.g., map rendering, basic combat).
