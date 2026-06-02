"""Authored skill and jutsu definitions with persistent character progress."""


DEFAULT_PRACTICE_POINTS = 5
DEFAULT_TRAINING_POINTS = 5


def create_technique_tables(cursor):
    """Create authored technique definitions and per-character progress."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            max_rank INTEGER NOT NULL DEFAULT 100,
            practice_cost INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jutsu_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jutsu_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            max_rank INTEGER NOT NULL DEFAULT 100,
            training_cost INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_skills (
            player_id INTEGER NOT NULL,
            skill_definition_id INTEGER NOT NULL,
            rank INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, skill_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (skill_definition_id) REFERENCES skill_definitions(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_jutsus (
            player_id INTEGER NOT NULL,
            jutsu_definition_id INTEGER NOT NULL,
            rank INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, jutsu_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (jutsu_definition_id) REFERENCES jutsu_definitions(id)
        )
        """
    )


def ensure_technique_player_columns(cursor):
    """Add persisted advancement-point pools to older player tables."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    for column_name, definition in (
        ("practice_points", f"INTEGER NOT NULL DEFAULT {DEFAULT_PRACTICE_POINTS}"),
        ("training_points", f"INTEGER NOT NULL DEFAULT {DEFAULT_TRAINING_POINTS}"),
    ):
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {column_name} {definition}")


def sync_skill_templates(cursor, templates):
    """Import authored ordinary-skill definitions."""
    for template in templates:
        cursor.execute(
            """
            INSERT INTO skill_definitions (
                skill_key, name, description, max_rank, practice_cost
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(skill_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                max_rank=excluded.max_rank,
                practice_cost=excluded.practice_cost
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                int(template.get("max_rank", 100)),
                int(template.get("practice_cost", 1)),
            ),
        )


def sync_jutsu_templates(cursor, templates):
    """Import authored jutsu definitions separately from ordinary skills."""
    for template in templates:
        cursor.execute(
            """
            INSERT INTO jutsu_definitions (
                jutsu_key, name, description, max_rank, training_cost
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(jutsu_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                max_rank=excluded.max_rank,
                training_cost=excluded.training_cost
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                int(template.get("max_rank", 100)),
                int(template.get("training_cost", 1)),
            ),
        )


def list_skills(cursor, username):
    """Return all authored ordinary skills and one character's progress."""
    return cursor.execute(
        """
        SELECT skill_definitions.id, skill_definitions.name,
               skill_definitions.description, skill_definitions.max_rank,
               skill_definitions.practice_cost, COALESCE(character_skills.rank, 0) AS rank,
               players.practice_points AS points
        FROM players
        CROSS JOIN skill_definitions
        LEFT JOIN character_skills
          ON character_skills.player_id = players.id
         AND character_skills.skill_definition_id = skill_definitions.id
        WHERE players.username=?
        ORDER BY skill_definitions.name COLLATE NOCASE
        """,
        (username,),
    ).fetchall()


def list_jutsus(cursor, username):
    """Return all authored jutsus and one character's progress."""
    return cursor.execute(
        """
        SELECT jutsu_definitions.id, jutsu_definitions.name,
               jutsu_definitions.description, jutsu_definitions.max_rank,
               jutsu_definitions.training_cost, COALESCE(character_jutsus.rank, 0) AS rank,
               players.training_points AS points
        FROM players
        CROSS JOIN jutsu_definitions
        LEFT JOIN character_jutsus
          ON character_jutsus.player_id = players.id
         AND character_jutsus.jutsu_definition_id = jutsu_definitions.id
        WHERE players.username=?
        ORDER BY jutsu_definitions.name COLLATE NOCASE
        """,
        (username,),
    ).fetchall()


def practice_skill(cursor, username, target):
    """Spend practice points to raise one authored ordinary skill."""
    return _advance(
        cursor,
        username,
        target,
        definitions_table="skill_definitions",
        definition_id="skill_definition_id",
        key_column="skill_key",
        progress_table="character_skills",
        cost_column="practice_cost",
        points_column="practice_points",
    )


def train_jutsu(cursor, username, target):
    """Spend training points to raise one authored jutsu."""
    return _advance(
        cursor,
        username,
        target,
        definitions_table="jutsu_definitions",
        definition_id="jutsu_definition_id",
        key_column="jutsu_key",
        progress_table="character_jutsus",
        cost_column="training_cost",
        points_column="training_points",
    )


def _advance(
    cursor,
    username,
    target,
    definitions_table,
    definition_id,
    key_column,
    progress_table,
    cost_column,
    points_column,
):
    player = cursor.execute(
        f"SELECT id, {points_column} FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}

    definitions = cursor.execute(
        f"SELECT id, name, max_rank, {cost_column} FROM {definitions_table} ORDER BY id"
    ).fetchall()
    definition = _resolve_named(definitions, target)
    if not definition:
        return {"status": "missing"}

    progress = cursor.execute(
        f"SELECT rank FROM {progress_table} WHERE player_id=? AND {definition_id}=?",
        (player["id"], definition["id"]),
    ).fetchone()
    rank = progress["rank"] if progress else 0
    if rank >= definition["max_rank"]:
        return {"status": "capped", "name": definition["name"], "rank": rank}
    if player[points_column] < definition[cost_column]:
        return {"status": "insufficient", "name": definition["name"]}

    rank += 1
    points = player[points_column] - definition[cost_column]
    try:
        cursor.execute(
            f"""
            INSERT INTO {progress_table} (player_id, {definition_id}, rank)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, {definition_id}) DO UPDATE SET rank=excluded.rank
            """,
            (player["id"], definition["id"], rank),
        )
        cursor.execute(
            f"UPDATE players SET {points_column}=? WHERE id=?",
            (points, player["id"]),
        )
        cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return {"status": "advanced", "name": definition["name"], "rank": rank, "points": points}


def _resolve_named(definitions, target):
    query = target.strip().casefold()
    if not query:
        return None
    exact = [definition for definition in definitions if definition["name"].casefold() == query]
    matches = exact or [
        definition
        for definition in definitions
        if definition["name"].casefold().startswith(query)
    ]
    return matches[0] if len(matches) == 1 else None
