# Shinobi_mud

**Shinobi_mud** is a text-based Multi-User Dungeon (MUD) game inspired by the Naruto universe. Players can interact, explore, and battle in a dynamic online world, engaging in social and combat scenarios.

## Features

- **Command System:** Separate modules for general, admin, and social commands.
- **Dynamic Zones:** Explore various areas and interact with the environment.
- **Multiplayer Support:** Engage with other players in real time.
- **Roleplay Elements:** Embrace your inner shinobi with unique abilities and narrative-driven gameplay.

## Getting Started

### Prerequisites

- **Python 3.8+**
- Linux, macOS, or Windows with terminal support for Python scripts.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ArrayParadigm/Shinobi_mud.git
   cd Shinobi_mud
   ```
2. Create and activate a virtual environment:

   Linux or macOS:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   python shinobi_mud.py
   ```

### Disposable Development Database

The SQLite database is local runtime state and is intentionally not committed to Git. Starting the server creates the configured database if it does not exist.

To start again with an empty development database:

```bash
python reset_dev_db.py
```

The reset helper moves the current database into `.local/db_backups/` before the next server launch creates a fresh one. This keeps test characters and experiments disposable while leaving a local recovery copy available when needed.

### Database Migrations

The server applies versioned SQLite migrations during startup. To apply migrations without starting the server:

```bash
python update_schema.py
```

### Promoting an Admin

New accounts are non-admin by default. After creating the first local account, promote it intentionally from the server terminal:

```bash
python promote_admin.py YourUsername
```

Restart the MUD or reconnect that character after promotion.

### Testing

Run the automated test suite from the project root:

```bash
python -m unittest discover -s tests -v
```

The tests use temporary or in-memory databases. They do not modify your local character database.

### Local Development Workflow

For a clean local test cycle:

```bash
python reset_dev_db.py
python -m unittest discover -s tests -v
python shinobi_mud.py
```

The server reads its TCP port from `config.json`.

### World Locations

The world map is persistent terrain. Player positions use `(x, y)` coordinates as the single source of truth.

Authored cities, dungeons, and other zones can be attached as optional overlays keyed by coordinates. Overlay metadata may include a zone name, VNUM, and room description without replacing or mutating the terrain underneath. This keeps open-world movement consistent while leaving room for drop-in areas later.

### Early Linux Testing

The current MUD socket uses plain-text TCP. Passwords are hashed safely in the database, but they are still sent over the network as plain text during login.

For early Linux testing, restrict access with a firewall allowlist, private network, or VPN. Do not expose password login to the open internet until encrypted transport is added.
