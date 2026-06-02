"""Authored skill and jutsu definitions with usage-based character progress."""


PROFICIENCY_TIERS = (
    (100, "Grandmaster"),
    (75, "Master"),
    (50, "Skilled"),
    (25, "Adept"),
    (0, "Novice"),
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
            is_available INTEGER NOT NULL DEFAULT 1
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
            PRIMARY KEY (player_id, jutsu_definition_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (jutsu_definition_id) REFERENCES jutsu_definitions(id)
        )
        """
    )
    ensure_usage_progress_columns(cursor)
    ensure_catalog_availability_columns(cursor)


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
                jutsu_key, name, description, usage_gain, is_available
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(jutsu_key) DO UPDATE SET
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


def proficiency_label(progress_percent):
    """Return the visible tier for a bounded usage percentage."""
    progress_percent = max(0, min(100, int(progress_percent)))
    for threshold, label in PROFICIENCY_TIERS:
        if progress_percent >= threshold:
            return label


def _list_progress(
    cursor,
    username,
    definitions_table,
    definition_id,
    progress_table,
    include_unavailable,
):
    return cursor.execute(
        f"""
        SELECT definitions.id, definitions.name, definitions.description,
               definitions.is_available,
               COALESCE(progress.progress_percent, 0) AS progress_percent
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


def _progress_detail(rows, target):
    definition = _resolve_named(rows, target)
    if not definition:
        return None
    return {
        "name": definition["name"],
        "description": definition["description"],
        "progress_percent": definition["progress_percent"],
        "proficiency": proficiency_label(definition["progress_percent"]),
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
        f"SELECT progress_percent FROM {progress_table} WHERE player_id=? AND {definition_id}=?",
        (player["id"], definition["id"]),
    ).fetchone()
    previous = progress["progress_percent"] if progress else 0
    updated = max(0, min(100, previous + definition["usage_gain"]))
    try:
        cursor.execute(
            f"""
            INSERT INTO {progress_table} (player_id, {definition_id}, progress_percent)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, {definition_id})
            DO UPDATE SET progress_percent=excluded.progress_percent
            """,
            (player["id"], definition["id"], updated),
        )
        if commit:
            cursor.connection.commit()
    except Exception:
        cursor.connection.rollback()
        raise
    return {
        "status": "recorded",
        "name": definition["name"],
        "progress_percent": updated,
        "proficiency": proficiency_label(updated),
    }


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
