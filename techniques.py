"""Authored skill and jutsu definitions with usage-based character progress."""


MAX_PROGRESS_POINTS = 100000
PRACTICE_POINT_GAIN = 10

PROFICIENCY_THRESHOLDS = (
    (100000, "Grandmaster"),
    (25001, "Master"),
    (5001, "Trained"),
    (1001, "Adept"),
    (101, "Novice"),
    (11, "Unlearned"),
    (0, "Untrained"),
)

PROFICIENCY_RANGES = (
    ("Untrained", 0, 10),
    ("Unlearned", 11, 100),
    ("Novice", 101, 1000),
    ("Adept", 1001, 5000),
    ("Trained", 5001, 25000),
    ("Master", 25001, 99999),
    ("Grandmaster", 100000, 100000),
)


def create_technique_tables(cursor):
    """Create authored technique definitions and per-character progress."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT NOT NULL,
            usage_gain INTEGER NOT NULL DEFAULT 1,
            is_available INTEGER NOT NULL DEFAULT 1,
            chakra_cost INTEGER NOT NULL DEFAULT 0,
            activation_seconds INTEGER NOT NULL DEFAULT 0,
            cooldown_seconds INTEGER NOT NULL DEFAULT 0,
            effect_key TEXT NOT NULL DEFAULT ''
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
            usage_gain INTEGER NOT NULL DEFAULT 1,
            is_available INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_skills (
            player_id INTEGER NOT NULL,
            skill_definition_id INTEGER NOT NULL,
            progress_percent INTEGER NOT NULL DEFAULT 0,
            progress_points INTEGER NOT NULL DEFAULT 0,
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
            progress_percent INTEGER NOT NULL DEFAULT 0,
            progress_points INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, jutsu_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (jutsu_definition_id) REFERENCES jutsu_definitions(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_jutsu_states (
            player_id INTEGER NOT NULL,
            jutsu_definition_id INTEGER NOT NULL,
            active_until TEXT,
            cooldown_until TEXT,
            PRIMARY KEY (player_id, jutsu_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (jutsu_definition_id) REFERENCES jutsu_definitions(id)
        )
        """
    )
    ensure_usage_progress_columns(cursor)
    ensure_catalog_availability_columns(cursor)
    ensure_jutsu_execution_columns(cursor)


def ensure_usage_progress_columns(cursor):
    """Upgrade the initial point-spend framework to usage progress."""
    for table_name in ("skill_definitions", "jutsu_definitions"):
        columns = {
            column[1]
            for column in cursor.execute(f"PRAGMA table_info({table_name})")
        }
        if "usage_gain" not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN usage_gain INTEGER NOT NULL DEFAULT 1"
            )

    for table_name in ("character_skills", "character_jutsus"):
        columns = {
            column[1]
            for column in cursor.execute(f"PRAGMA table_info({table_name})")
        }
        if "progress_percent" not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0"
            )
            if "rank" in columns:
                cursor.execute(
                    f"UPDATE {table_name} SET progress_percent=MIN(100, MAX(0, rank))"
                )
        columns = {
            column[1]
            for column in cursor.execute(f"PRAGMA table_info({table_name})")
        }
        if "progress_points" not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN progress_points INTEGER NOT NULL DEFAULT 0"
            )
            cursor.execute(
                f"""
                UPDATE {table_name}
                SET progress_points=CASE
                    WHEN progress_percent >= 100 THEN {MAX_PROGRESS_POINTS}
                    ELSE MAX(0, progress_percent * 1000)
                END
                """
            )


def ensure_catalog_availability_columns(cursor):
    """Mark catalog-only placeholders without making them trainable."""
    for table_name in ("skill_definitions", "jutsu_definitions"):
        columns = {
            column[1]
            for column in cursor.execute(f"PRAGMA table_info({table_name})")
        }
        if "is_available" not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN is_available INTEGER NOT NULL DEFAULT 1"
            )


def ensure_jutsu_execution_columns(cursor):
    """Add authored execution metadata and persisted defensive state."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(jutsu_definitions)")
    }
    for column_name, definition in (
        ("chakra_cost", "INTEGER NOT NULL DEFAULT 0"),
        ("activation_seconds", "INTEGER NOT NULL DEFAULT 0"),
        ("cooldown_seconds", "INTEGER NOT NULL DEFAULT 0"),
        ("effect_key", "TEXT NOT NULL DEFAULT ''"),
    ):
        if column_name not in columns:
            cursor.execute(
                f"ALTER TABLE jutsu_definitions ADD COLUMN {column_name} {definition}"
            )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_jutsu_states (
            player_id INTEGER NOT NULL,
            jutsu_definition_id INTEGER NOT NULL,
            active_until TEXT,
            cooldown_until TEXT,
            PRIMARY KEY (player_id, jutsu_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (jutsu_definition_id) REFERENCES jutsu_definitions(id)
        )
        """
    )


def sync_skill_templates(cursor, templates):
    """Import authored ordinary-skill definitions."""
    for template in templates:
        cursor.execute(
            """
            INSERT INTO skill_definitions (
                skill_key, name, description, usage_gain, is_available
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(skill_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                usage_gain=excluded.usage_gain,
                is_available=excluded.is_available
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                int(template.get("usage_gain", 1)),
                int(template.get("available", True)),
            ),
        )


def sync_jutsu_templates(cursor, templates):
    """Import authored jutsu definitions separately from ordinary skills."""
    for template in templates:
        cursor.execute(
            """
            INSERT INTO jutsu_definitions (
                jutsu_key, name, description, usage_gain, is_available,
                chakra_cost, activation_seconds, cooldown_seconds, effect_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(jutsu_key) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                usage_gain=excluded.usage_gain,
                is_available=excluded.is_available,
                chakra_cost=excluded.chakra_cost,
                activation_seconds=excluded.activation_seconds,
                cooldown_seconds=excluded.cooldown_seconds,
                effect_key=excluded.effect_key
            """,
            (
                template["key"],
                template["name"],
                template["description"],
                int(template.get("usage_gain", 1)),
                int(template.get("available", True)),
                int(template.get("chakra_cost", 0)),
                int(template.get("activation_seconds", 0)),
                int(template.get("cooldown_seconds", 0)),
                template.get("effect_key", ""),
            ),
        )


def list_skills(cursor, username, include_unavailable=False):
    """Return all authored ordinary skills and one character's progress."""
    return _list_progress(
        cursor,
        username,
        definitions_table="skill_definitions",
        definition_id="skill_definition_id",
        progress_table="character_skills",
        include_unavailable=include_unavailable,
    )


def list_jutsus(cursor, username, include_unavailable=False):
    """Return all authored jutsus and one character's progress."""
    return _list_progress(
        cursor,
        username,
        definitions_table="jutsu_definitions",
        definition_id="jutsu_definition_id",
        progress_table="character_jutsus",
        include_unavailable=include_unavailable,
    )


def skill_detail(cursor, username, target):
    """Return one ordinary skill's visible usage progress."""
    return _progress_detail(list_skills(cursor, username), target)


def jutsu_detail(cursor, username, target):
    """Return one jutsu's visible usage progress."""
    return _progress_detail(list_jutsus(cursor, username), target)


def record_skill_use(cursor, username, skill_key, commit=True):
    """Increase one ordinary skill after valid gameplay use."""
    return _record_use(
        cursor,
        username,
        skill_key,
        definitions_table="skill_definitions",
        key_column="skill_key",
        definition_id="skill_definition_id",
        progress_table="character_skills",
        commit=commit,
    )


def record_jutsu_use(cursor, username, jutsu_key, commit=True):
    """Increase one jutsu after valid gameplay use."""
    return _record_use(
        cursor,
        username,
        jutsu_key,
        definitions_table="jutsu_definitions",
        key_column="jutsu_key",
        definition_id="jutsu_definition_id",
        progress_table="character_jutsus",
        commit=commit,
    )


def practice_skill(cursor, username, target):
    """Advance one available skill through deliberate practice."""
    return _practice(
        cursor,
        username,
        target,
        definitions_table="skill_definitions",
        definition_id="skill_definition_id",
        progress_table="character_skills",
    )


def train_jutsu(cursor, username, target):
    """Advance one available jutsu through deliberate training."""
    return _practice(
        cursor,
        username,
        target,
        definitions_table="jutsu_definitions",
        definition_id="jutsu_definition_id",
        progress_table="character_jutsus",
    )


def activate_jutsu(cursor, username, target):
    """Spend chakra and persist one authored jutsu activation window."""
    connection = cursor.connection
    try:
        cursor.execute("BEGIN IMMEDIATE")
        player = cursor.execute(
            "SELECT id, chakra FROM players WHERE username=?",
            (username,),
        ).fetchone()
        if not player:
            connection.rollback()
            return {"status": "missing_player"}
        definition = _resolve_named(
            cursor.execute(
                """
                SELECT id, jutsu_key, name, chakra_cost, activation_seconds,
                       cooldown_seconds, effect_key
                FROM jutsu_definitions
                WHERE is_available=1
                ORDER BY id
                """
            ).fetchall(),
            target,
        )
        if not definition:
            connection.rollback()
            return {"status": "missing"}
        if not definition["effect_key"]:
            connection.rollback()
            return {"status": "unimplemented", "name": definition["name"]}
        state = cursor.execute(
            """
            SELECT active_until, cooldown_until,
                   active_until > CURRENT_TIMESTAMP AS active,
                   cooldown_until > CURRENT_TIMESTAMP AS cooling_down
            FROM character_jutsu_states
            WHERE player_id=? AND jutsu_definition_id=?
            """,
            (player["id"], definition["id"]),
        ).fetchone()
        if state and state["active"]:
            connection.rollback()
            return {"status": "active", "name": definition["name"]}
        if state and state["cooling_down"]:
            connection.rollback()
            return {"status": "cooldown", "name": definition["name"]}
        if player["chakra"] < definition["chakra_cost"]:
            connection.rollback()
            return {"status": "insufficient_chakra", "name": definition["name"]}
        cursor.execute(
            "UPDATE players SET chakra=chakra-? WHERE id=?",
            (definition["chakra_cost"], player["id"]),
        )
        cursor.execute(
            """
            INSERT INTO character_jutsu_states (
                player_id, jutsu_definition_id, active_until, cooldown_until
            )
            VALUES (
                ?, ?,
                datetime('now', '+' || ? || ' seconds'),
                datetime('now', '+' || ? || ' seconds')
            )
            ON CONFLICT(player_id, jutsu_definition_id) DO UPDATE SET
                active_until=excluded.active_until,
                cooldown_until=excluded.cooldown_until
            """,
            (
                player["id"],
                definition["id"],
                definition["activation_seconds"],
                definition["cooldown_seconds"],
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "status": "activated",
        "name": definition["name"],
        "chakra": player["chakra"] - definition["chakra_cost"],
        "active_seconds": definition["activation_seconds"],
        "cooldown_seconds": definition["cooldown_seconds"],
    }


def consume_substitution(cursor, username):
    """Consume an active Substitution defense and record successful use."""
    state = cursor.execute(
        """
        SELECT states.player_id, states.jutsu_definition_id
        FROM character_jutsu_states AS states
        JOIN players ON players.id=states.player_id
        JOIN jutsu_definitions ON jutsu_definitions.id=states.jutsu_definition_id
        WHERE players.username=?
          AND jutsu_definitions.effect_key='substitution'
          AND states.active_until > CURRENT_TIMESTAMP
        """,
        (username,),
    ).fetchone()
    if not state:
        return None
    cursor.execute(
        """
        UPDATE character_jutsu_states
        SET active_until=NULL
        WHERE player_id=? AND jutsu_definition_id=?
        """,
        (state["player_id"], state["jutsu_definition_id"]),
    )
    return record_jutsu_use(
        cursor,
        username,
        "substitution-technique",
        commit=False,
    )


def tick_jutsu_states(connection):
    """Clear expired activation windows while retaining active cooldowns."""
    cursor = connection.execute(
        """
        UPDATE character_jutsu_states
        SET active_until=NULL
        WHERE active_until IS NOT NULL
          AND active_until <= CURRENT_TIMESTAMP
        """
    )
    connection.execute(
        """
        DELETE FROM character_jutsu_states
        WHERE active_until IS NULL
          AND cooldown_until <= CURRENT_TIMESTAMP
        """
    )
    connection.commit()
    return cursor.rowcount


def proficiency_label(progress_points):
    """Return the visible tier for point-based progress."""
    progress_points = max(0, min(MAX_PROGRESS_POINTS, int(progress_points)))
    for threshold, label in PROFICIENCY_THRESHOLDS:
        if progress_points >= threshold:
            return label


def progress_percent_for_points(progress_points):
    """Return visible percentage through the current proficiency band."""
    points = max(0, min(MAX_PROGRESS_POINTS, int(progress_points)))
    for label, start, end in PROFICIENCY_RANGES:
        if start <= points <= end:
            if start == end:
                return 100
            return int(((points - start) / (end - start)) * 100)
    return 0


def _list_progress(
    cursor,
    username,
    definitions_table,
    definition_id,
    progress_table,
    include_unavailable,
):
    rows = cursor.execute(
        f"""
        SELECT definitions.id, definitions.name, definitions.description,
               definitions.is_available,
               COALESCE(progress.progress_points, progress.progress_percent, 0) AS progress_points
        FROM players
        CROSS JOIN {definitions_table} AS definitions
        LEFT JOIN {progress_table} AS progress
          ON progress.player_id = players.id
         AND progress.{definition_id} = definitions.id
        WHERE players.username=? AND (? OR definitions.is_available=1)
        ORDER BY definitions.name COLLATE NOCASE
        """,
        (username, include_unavailable),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "is_available": row["is_available"],
            "progress_points": row["progress_points"],
            "progress_percent": progress_percent_for_points(row["progress_points"]),
        }
        for row in rows
    ]


def _progress_detail(rows, target):
    definition = _resolve_named(rows, target)
    if not definition:
        return None
    return {
        "name": definition["name"],
        "description": definition["description"],
        "progress_percent": definition["progress_percent"],
        "progress_points": definition["progress_points"],
        "proficiency": proficiency_label(definition["progress_points"]),
    }


def _record_use(
    cursor,
    username,
    technique_key,
    definitions_table,
    key_column,
    definition_id,
    progress_table,
    commit,
):
    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}
    definition = cursor.execute(
        f"""
        SELECT id, name, usage_gain
        FROM {definitions_table}
        WHERE {key_column}=? AND is_available=1
        """,
        (technique_key,),
    ).fetchone()
    if not definition:
        return {"status": "missing"}
    progress = cursor.execute(
        f"SELECT progress_percent, progress_points FROM {progress_table} WHERE player_id=? AND {definition_id}=?",
        (player["id"], definition["id"]),
    ).fetchone()
    previous = _progress_points_from_row(progress)
    updated = max(0, min(MAX_PROGRESS_POINTS, previous + definition["usage_gain"]))
    updated_percent = progress_percent_for_points(updated)
    try:
        cursor.execute(
            f"""
            INSERT INTO {progress_table} (player_id, {definition_id}, progress_percent, progress_points)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id, {definition_id})
            DO UPDATE SET
                progress_percent=excluded.progress_percent,
                progress_points=excluded.progress_points
            """,
            (player["id"], definition["id"], updated_percent, updated),
        )
        if commit:
            cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return {
        "status": "recorded",
        "name": definition["name"],
        "progress_points": updated,
        "progress_percent": updated_percent,
        "proficiency": proficiency_label(updated),
    }


def _practice(cursor, username, target, definitions_table, definition_id, progress_table):
    player = cursor.execute(
        "SELECT id FROM players WHERE username=?",
        (username,),
    ).fetchone()
    if not player:
        return {"status": "missing_player"}
    definition = _resolve_named(
        cursor.execute(
            f"""
            SELECT id, name, description, is_available
            FROM {definitions_table}
            WHERE is_available=1
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall(),
        target,
    )
    if not definition:
        return {"status": "missing"}
    progress = cursor.execute(
        f"SELECT progress_percent, progress_points FROM {progress_table} WHERE player_id=? AND {definition_id}=?",
        (player["id"], definition["id"]),
    ).fetchone()
    previous_points = _progress_points_from_row(progress)
    previous_percent = progress_percent_for_points(previous_points)
    previous_label = proficiency_label(previous_points)
    updated_points = min(MAX_PROGRESS_POINTS, previous_points + PRACTICE_POINT_GAIN)
    updated_percent = progress_percent_for_points(updated_points)
    updated_label = proficiency_label(updated_points)
    cursor.execute(
        f"""
        INSERT INTO {progress_table} (player_id, {definition_id}, progress_percent, progress_points)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(player_id, {definition_id})
        DO UPDATE SET
            progress_percent=excluded.progress_percent,
            progress_points=excluded.progress_points
        """,
        (player["id"], definition["id"], updated_percent, updated_points),
    )
    cursor.connection.commit()
    milestones = []
    if updated_label != previous_label:
        milestones.append("tier")
    elif updated_percent // 10 > previous_percent // 10:
        milestones.append("ten_percent")
    return {
        "status": "practiced",
        "name": definition["name"],
        "progress_points": updated_points,
        "progress_percent": updated_percent,
        "proficiency": updated_label,
        "milestones": milestones,
    }


def _progress_points_from_row(progress):
    if not progress:
        return 0
    if "progress_points" in progress.keys():
        points = progress["progress_points"]
        if points or progress["progress_percent"] <= 0:
            return points
    return min(MAX_PROGRESS_POINTS, max(0, progress["progress_percent"] * 1000))


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
