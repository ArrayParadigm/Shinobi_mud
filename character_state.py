"""Persistent character appearance, reproductive state, and injuries."""

from datetime import datetime, timedelta, timezone
import random

from presentation import sanitize_player_text


FEATURE_FIELDS = ("hair", "eyes", "height", "build", "complexion", "marks")
REPRODUCTIVE_ROLES = {"none", "can_carry", "can_impregnate", "both"}
PREGNANCY_STATUSES = {"none", "pregnant"}
PREGNANCY_STAGES = {"none", "early", "middle", "late"}
VISIBLE_PREGNANCY_STAGES = {"middle", "late"}
DEFAULT_CYCLE_LENGTH = 28
FERTILE_DAYS = {12, 13, 14, 15, 16}
FERTILE_CHANCE = 35
LOW_CHANCE = 5
PREGNANCY_DAYS = 280

INJURY_DEFINITIONS = {
    "missing_left_arm": {"label": "missing left arm", "obvious": True, "arms": True},
    "missing_right_arm": {"label": "missing right arm", "obvious": True, "arms": True},
    "missing_left_hand": {"label": "missing left hand", "obvious": True, "hands": True},
    "missing_right_hand": {"label": "missing right hand", "obvious": True, "hands": True},
    "missing_left_leg": {"label": "missing left leg", "obvious": True, "movement": True},
    "missing_right_leg": {"label": "missing right leg", "obvious": True, "movement": True},
    "missing_left_foot": {"label": "missing left foot", "obvious": True, "movement": True},
    "missing_right_foot": {"label": "missing right foot", "obvious": True, "movement": True},
    "blind": {"label": "blind", "obvious": True, "sight": True},
    "blindfolded": {"label": "blindfolded", "obvious": True, "sight": True},
    "gagged": {"label": "gagged", "obvious": True, "speech": True},
    "mute": {"label": "mute", "obvious": False, "speech": True},
    "scarred": {"label": "scarred", "obvious": True},
    "chronic_limp": {"label": "chronic limp", "obvious": True, "movement": True},
    "knocked_out": {"label": "knocked out", "obvious": True, "movement": True, "unconscious": True},
}


def create_character_state_tables(cursor):
    _ensure_player_columns(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS character_injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            injury_key TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, injury_key)
        )
        """
    )


def _ensure_player_columns(cursor):
    columns = {column[1] for column in cursor.execute("PRAGMA table_info(players)")}
    for column, definition in (
        ("hair", "TEXT NOT NULL DEFAULT 'unspecified'"),
        ("eyes", "TEXT NOT NULL DEFAULT 'unspecified'"),
        ("height", "TEXT NOT NULL DEFAULT 'medium'"),
        ("build", "TEXT NOT NULL DEFAULT 'average'"),
        ("complexion", "TEXT NOT NULL DEFAULT 'unspecified'"),
        ("marks", "TEXT NOT NULL DEFAULT 'none'"),
        ("reproductive_role", "TEXT NOT NULL DEFAULT 'none'"),
        ("cycle_day", "INTEGER NOT NULL DEFAULT 1"),
        ("cycle_length", f"INTEGER NOT NULL DEFAULT {DEFAULT_CYCLE_LENGTH}"),
        ("last_cycle_update", "TEXT"),
        ("pregnancy_status", "TEXT NOT NULL DEFAULT 'none'"),
        ("pregnancy_started_at", "TEXT"),
        ("pregnancy_stage", "TEXT NOT NULL DEFAULT 'none'"),
        ("pregnancy_partner", "TEXT NOT NULL DEFAULT ''"),
        ("pregnancy_due_at", "TEXT"),
    ):
        if column not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {column} {definition}")


def feature_state(cursor, username):
    return cursor.execute(
        """
        SELECT username, description, hair, eyes, height, build, complexion, marks,
               reproductive_role, cycle_day, cycle_length, last_cycle_update,
               pregnancy_status, pregnancy_started_at, pregnancy_stage,
               pregnancy_partner, pregnancy_due_at
        FROM players
        WHERE username=? COLLATE NOCASE
        """,
        (username,),
    ).fetchone()


def set_feature(cursor, username, field, value):
    field = field.strip().lower()
    if field not in FEATURE_FIELDS:
        raise ValueError("Feature must be hair, eyes, height, build, complexion, or marks.")
    text = sanitize_player_text(value).strip()
    if not text:
        raise ValueError("Feature value cannot be empty.")
    cursor.execute(f"UPDATE players SET {field}=? WHERE username=? COLLATE NOCASE", (text, username))
    cursor.connection.commit()


def set_reproductive_field(cursor, username, field, value):
    field = field.strip().lower()
    if field == "reproductive_role":
        normalized = _normalize_value(value)
        if normalized not in REPRODUCTIVE_ROLES:
            raise ValueError(f"Reproductive role must be one of: {', '.join(sorted(REPRODUCTIVE_ROLES))}.")
        cursor.execute("UPDATE players SET reproductive_role=? WHERE username=? COLLATE NOCASE", (normalized, username))
    elif field == "cycle_day":
        cycle_day = int(value)
        if cycle_day < 1 or cycle_day > 60:
            raise ValueError("cycle_day must be between 1 and 60.")
        cursor.execute("UPDATE players SET cycle_day=? WHERE username=? COLLATE NOCASE", (cycle_day, username))
    elif field == "cycle_length":
        cycle_length = int(value)
        if cycle_length < 1 or cycle_length > 60:
            raise ValueError("cycle_length must be between 1 and 60.")
        cursor.execute("UPDATE players SET cycle_length=? WHERE username=? COLLATE NOCASE", (cycle_length, username))
    elif field == "pregnancy_status":
        normalized = _normalize_value(value)
        if normalized not in PREGNANCY_STATUSES:
            raise ValueError("pregnancy_status must be none or pregnant.")
        if normalized == "none":
            clear_pregnancy(cursor, username)
            return
        _set_pregnancy(cursor, username, "", "early")
    elif field == "pregnancy_stage":
        normalized = _normalize_value(value)
        if normalized not in PREGNANCY_STAGES:
            raise ValueError(f"pregnancy_stage must be one of: {', '.join(sorted(PREGNANCY_STAGES))}.")
        cursor.execute("UPDATE players SET pregnancy_stage=? WHERE username=? COLLATE NOCASE", (normalized, username))
    elif field == "pregnancy_partner":
        cursor.execute(
            "UPDATE players SET pregnancy_partner=? WHERE username=? COLLATE NOCASE",
            (sanitize_player_text(value).strip(), username),
        )
    else:
        raise ValueError("Unsupported reproductive field.")
    cursor.connection.commit()


def clear_pregnancy(cursor, username):
    cursor.execute(
        """
        UPDATE players
        SET pregnancy_status='none', pregnancy_started_at=NULL, pregnancy_stage='none',
            pregnancy_partner='', pregnancy_due_at=NULL
        WHERE username=? COLLATE NOCASE
        """,
        (username,),
    )
    cursor.connection.commit()


def add_injury(cursor, username, injury_key, note=""):
    injury_key = _normalize_value(injury_key)
    if injury_key not in INJURY_DEFINITIONS:
        raise ValueError(f"Unsupported injury: {injury_key}")
    cursor.execute(
        """
        INSERT INTO character_injuries (username, injury_key, note)
        VALUES (?, ?, ?)
        ON CONFLICT(username, injury_key) DO UPDATE SET note=excluded.note
        """,
        (username, injury_key, sanitize_player_text(note)),
    )
    cursor.connection.commit()


def clear_injury(cursor, username, injury_key):
    injury_key = _normalize_value(injury_key)
    if injury_key == "all":
        cursor.execute("DELETE FROM character_injuries WHERE username=? COLLATE NOCASE", (username,))
    else:
        cursor.execute(
            "DELETE FROM character_injuries WHERE username=? COLLATE NOCASE AND injury_key=?",
            (username, injury_key),
        )
    cursor.connection.commit()


def injury_rows(cursor, username):
    return cursor.execute(
        """
        SELECT injury_key, note, created_at
        FROM character_injuries
        WHERE username=? COLLATE NOCASE
        ORDER BY injury_key
        """,
        (username,),
    ).fetchall()


def injury_keys(cursor, username):
    return {row["injury_key"] for row in injury_rows(cursor, username)}


def injury_labels(keys):
    return [INJURY_DEFINITIONS[key]["label"] for key in sorted(keys) if key in INJURY_DEFINITIONS]


def movement_block(cursor, username, assisted=False):
    keys = injury_keys(cursor, username)
    if "knocked_out" in keys and not assisted:
        return "You are knocked out and cannot move without help."
    if any(INJURY_DEFINITIONS[key].get("movement") for key in keys if key in INJURY_DEFINITIONS) and not assisted:
        return "Your injuries prevent ordinary movement. You need support, guidance, or to be carried."
    return ""


def speech_block(cursor, username):
    keys = injury_keys(cursor, username)
    if any(INJURY_DEFINITIONS[key].get("speech") for key in keys if key in INJURY_DEFINITIONS):
        return "You cannot speak clearly right now."
    return ""


def sight_block(cursor, username):
    keys = injury_keys(cursor, username)
    if any(INJURY_DEFINITIONS[key].get("sight") for key in keys if key in INJURY_DEFINITIONS):
        return "Your vision is blocked."
    return ""


def visible_profile(cursor, username):
    row = feature_state(cursor, username)
    if not row:
        return None
    keys = injury_keys(cursor, username)
    lines = [
        f"You see {row['username']}.",
        row["description"],
        (
            f"Features: hair={row['hair']} eyes={row['eyes']} height={row['height']} "
            f"build={row['build']} complexion={row['complexion']} marks={row['marks']}"
        ),
    ]
    obvious = injury_labels(key for key in keys if INJURY_DEFINITIONS.get(key, {}).get("obvious"))
    if obvious:
        lines.append(f"Obvious injuries: {', '.join(obvious)}.")
    if row["pregnancy_status"] == "pregnant" and row["pregnancy_stage"] in VISIBLE_PREGNANCY_STAGES:
        lines.append(f"Pregnancy: visibly {row['pregnancy_stage']} stage.")
    return lines


def private_pregnancy_summary(cursor, username):
    row = feature_state(cursor, username)
    if not row:
        return ["Pregnancy state is unavailable."]
    if row["pregnancy_status"] != "pregnant":
        return ["Pregnancy: none."]
    return [
        f"Pregnancy: {row['pregnancy_stage']} stage.",
        f"Partner: {row['pregnancy_partner'] or 'unknown'}",
        f"Due: {row['pregnancy_due_at'] or 'unknown'}",
    ]


def private_biology_summary(cursor, username):
    row = feature_state(cursor, username)
    if not row:
        return []
    return [
        f"Reproductive role: {row['reproductive_role']}",
        f"Cycle: day {row['cycle_day']} of {row['cycle_length']}",
    ]


def maybe_apply_pregnancy(cursor, actor_username, target_username, risk_flag, rng=None):
    if not risk_flag:
        return {"rolled": False, "pregnant": False, "reason": "no_risk"}
    actor = feature_state(cursor, actor_username)
    target = feature_state(cursor, target_username)
    if not actor or not target:
        return {"rolled": False, "pregnant": False, "reason": "missing"}
    carrier, partner = _pregnancy_pair(actor, target)
    if not carrier:
        return {"rolled": False, "pregnant": False, "reason": "incompatible"}
    if carrier["pregnancy_status"] == "pregnant":
        return {"rolled": False, "pregnant": False, "reason": "already_pregnant"}
    chance = FERTILE_CHANCE if int(carrier["cycle_day"]) in FERTILE_DAYS else LOW_CHANCE
    roller = rng or random
    if roller.randint(1, 100) <= chance:
        _set_pregnancy(cursor, carrier["username"], partner["username"], "early")
        cursor.connection.commit()
        return {"rolled": True, "pregnant": True, "carrier": carrier["username"], "chance": chance}
    return {"rolled": True, "pregnant": False, "carrier": carrier["username"], "chance": chance}


def _pregnancy_pair(actor, target):
    actor_role = actor["reproductive_role"]
    target_role = target["reproductive_role"]
    actor_can_impregnate = actor_role in {"can_impregnate", "both"}
    target_can_carry = target_role in {"can_carry", "both"}
    target_can_impregnate = target_role in {"can_impregnate", "both"}
    actor_can_carry = actor_role in {"can_carry", "both"}
    if actor_can_impregnate and target_can_carry:
        return target, actor
    if target_can_impregnate and actor_can_carry:
        return actor, target
    return None, None


def _set_pregnancy(cursor, username, partner, stage):
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=PREGNANCY_DAYS)
    cursor.execute(
        """
        UPDATE players
        SET pregnancy_status='pregnant', pregnancy_started_at=?, pregnancy_stage=?,
            pregnancy_partner=?, pregnancy_due_at=?
        WHERE username=? COLLATE NOCASE
        """,
        (
            now.isoformat(timespec="seconds"),
            stage,
            partner,
            due.date().isoformat(),
            username,
        ),
    )


def _normalize_value(value):
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
