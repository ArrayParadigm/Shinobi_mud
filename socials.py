"""Catalog-backed social actions, consent settings, and active social states."""

from datetime import datetime, timezone
import json

from locations import (
    LocationPersistenceError,
    coordinate_key,
    destination_for,
    is_within_bounds,
    relocate_player,
)
from presentation import sanitize_player_text


DEFAULT_VISIBLE_CATEGORIES = {"normal", "friendly", "playful", "utility"}
ADULT_CATEGORIES = {"intimate", "bdsm"}
CONSENT_CATEGORIES = DEFAULT_VISIBLE_CATEGORIES | ADULT_CATEGORIES | {"mechanical", "restrictive"}
CONSENT_ALLOW = "allow"
CONSENT_DENY = "deny"
STATE_HOLD_HANDS = "holdhands"
STATE_RESTRAINED = "restrained"
STATE_GAGGED = "gagged"
STATE_BLINDFOLDED = "blindfolded"
MOVEMENT_STATE_TYPES = {"holdhands", "carry", "support", "guide", "drag", "escort"}


def _social(
    key,
    category="normal",
    target=False,
    consent=False,
    adult=False,
    mechanical="",
    self_message="",
    room_message="",
    target_message="",
    actor_message="",
    speech=False,
    mobile=False,
    move_disabled=False,
    pregnancy=False,
):
    return {
        "key": key,
        "category": category,
        "target_required": 1 if target else 0,
        "requires_consent": 1 if consent else 0,
        "adult": 1 if adult else 0,
        "mechanical": mechanical,
        "self_message": self_message or f"You {key}.",
        "room_message": room_message or f"{{actor}} {key}s.",
        "target_message": target_message,
        "actor_message": actor_message,
        "speech_blocked_by_gag": 1 if speech else 0,
        "requires_mobile_actor": 1 if mobile else 0,
        "can_move_disabled_target": 1 if move_disabled else 0,
        "pregnancy_risk": 1 if pregnancy else 0,
    }


REGULAR_SOCIAL_NAMES = (
    "wave", "smile", "nod", "bow", "laugh", "salute", "shrug", "cheer", "clap", "sigh",
    "grin", "frown", "wink", "yawn", "stretch", "ponder", "snicker", "applaud", "whistle", "dance",
    "pose", "point", "beckon", "thank", "apologize", "greet", "farewell", "blush", "glare", "stare",
    "peer", "listen", "hum", "sing", "chant", "pray", "meditate", "sit", "stand", "lean",
    "pace", "bounce", "shiver", "sweat", "cough", "sneeze", "smirk", "mutter", "compliment", "encourage",
)

TARGETED_REGULARS = {"point", "beckon", "thank", "apologize", "greet", "farewell", "glare", "stare", "peer", "compliment", "encourage"}
SPEECH_REGULARS = {"thank", "apologize", "greet", "farewell", "mutter", "compliment", "encourage", "sing", "chant"}

ADULT_SOCIALS = (
    "kiss", "deepkiss", "caress", "fondle", "tease", "straddle", "lapdance", "grind", "spoon",
    "makeout", "undress", "afterglow", "intimate", "claim", "breed",
)

BONDAGE_SOCIALS = {
    "gag": STATE_GAGGED,
    "ungag": STATE_GAGGED,
    "blindfold": STATE_BLINDFOLDED,
    "bindwrists": STATE_RESTRAINED,
    "bindankles": STATE_RESTRAINED,
}

MOVEMENT_SOCIALS = {
    "carry": "carry",
    "support": "support",
    "guide": "guide",
    "drag": "drag",
    "escort": "escort",
}


DEFAULT_SOCIALS = tuple(
    [_social(name, target=name in TARGETED_REGULARS, speech=name in SPEECH_REGULARS) for name in REGULAR_SOCIAL_NAMES]
    + [
        _social("hug", "friendly", target=True, consent=True, room_message="{actor} hugs {target}.", target_message="{actor} hugs you.", actor_message="You hug {target}."),
        _social("highfive", "friendly", target=True, room_message="{actor} high-fives {target}.", target_message="{actor} high-fives you.", actor_message="You high-five {target}."),
        _social("pat", "playful", target=True, consent=True, room_message="{actor} gives {target} a playful pat.", target_message="{actor} gives you a playful pat.", actor_message="You give {target} a playful pat."),
        _social("poke", "playful", target=True, room_message="{actor} pokes {target}.", target_message="{actor} pokes you.", actor_message="You poke {target}."),
        _social("nuzzle", "intimate", target=True, consent=True, adult=True, room_message="{actor} nuzzles {target}.", target_message="{actor} nuzzles you.", actor_message="You nuzzle {target}."),
        _social("cuddle", "intimate", target=True, consent=True, adult=True, room_message="{actor} cuddles close with {target}.", target_message="{actor} cuddles close with you.", actor_message="You cuddle close with {target}."),
        _social("holdhands", "utility", target=True, consent=True, mechanical=STATE_HOLD_HANDS, mobile=True, move_disabled=True,
                room_message="{actor} takes {target}'s hand.",
                target_message="{actor} takes your hand.",
                actor_message="You take {target}'s hand."),
        _social("tie", "bdsm", target=True, consent=True, adult=True, mechanical=STATE_RESTRAINED,
                room_message="{actor} restrains {target}.",
                target_message="{actor} restrains you.",
                actor_message="You restrain {target}."),
        _social("restrain", "bdsm", target=True, consent=True, adult=True, mechanical=STATE_RESTRAINED,
                room_message="{actor} restrains {target}.",
                target_message="{actor} restrains you.",
                actor_message="You restrain {target}."),
        *[
            _social(name, "intimate", target=True, consent=True, adult=True, pregnancy=(name == "breed"),
                    room_message=f"{{actor}} shares an intimate {name} with {{target}}.",
                    target_message=f"{{actor}} shares an intimate {name} with you.",
                    actor_message=f"You share an intimate {name} with {{target}}.")
            for name in ADULT_SOCIALS
        ],
        *[
            _social(name, "bdsm", target=True, consent=True, adult=True, mechanical=state,
                    room_message=f"{{actor}} applies {name} to {{target}}.",
                    target_message=f"{{actor}} applies {name} to you.",
                    actor_message=f"You apply {name} to {{target}}.")
            for name, state in BONDAGE_SOCIALS.items()
        ],
        *[
            _social(name, "utility", target=True, consent=True, mechanical=state, mobile=True, move_disabled=True,
                    room_message=f"{{actor}} prepares to {name} {{target}}.",
                    target_message=f"{{actor}} prepares to {name} you.",
                    actor_message=f"You prepare to {name} {{target}}.")
            for name, state in MOVEMENT_SOCIALS.items()
        ],
        _social("kneel", "bdsm", adult=True, self_message="You kneel.", room_message="{actor} kneels."),
    ]
)


def create_social_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS social_templates (
            social_key TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT 'normal',
            target_required INTEGER NOT NULL DEFAULT 0,
            requires_consent INTEGER NOT NULL DEFAULT 0,
            adult INTEGER NOT NULL DEFAULT 0,
            mechanical TEXT NOT NULL DEFAULT '',
            self_message TEXT NOT NULL DEFAULT '',
            room_message TEXT NOT NULL DEFAULT '',
            target_message TEXT NOT NULL DEFAULT '',
            actor_message TEXT NOT NULL DEFAULT '',
            speech_blocked_by_gag INTEGER NOT NULL DEFAULT 0,
            requires_mobile_actor INTEGER NOT NULL DEFAULT 0,
            can_move_disabled_target INTEGER NOT NULL DEFAULT 0,
            pregnancy_risk INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS social_consent (
            username TEXT NOT NULL,
            scope TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (username, scope, target)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS social_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            target TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (state_type, actor, target)
        )
        """
    )
    _ensure_social_columns(cursor)
    seed_default_socials(cursor)


def _ensure_social_columns(cursor):
    columns = {column[1] for column in cursor.execute("PRAGMA table_info(social_templates)")}
    for column, definition in (
        ("speech_blocked_by_gag", "INTEGER NOT NULL DEFAULT 0"),
        ("requires_mobile_actor", "INTEGER NOT NULL DEFAULT 0"),
        ("can_move_disabled_target", "INTEGER NOT NULL DEFAULT 0"),
        ("pregnancy_risk", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if column not in columns:
            cursor.execute(f"ALTER TABLE social_templates ADD COLUMN {column} {definition}")


def seed_default_socials(cursor):
    for template in DEFAULT_SOCIALS:
        cursor.execute(
            """
            INSERT INTO social_templates (
                social_key, category, target_required, requires_consent, adult,
                mechanical, self_message, room_message, target_message, actor_message,
                speech_blocked_by_gag, requires_mobile_actor, can_move_disabled_target,
                pregnancy_risk
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(social_key) DO UPDATE SET
                category=excluded.category,
                target_required=excluded.target_required,
                requires_consent=excluded.requires_consent,
                adult=excluded.adult,
                mechanical=excluded.mechanical,
                self_message=excluded.self_message,
                room_message=excluded.room_message,
                target_message=excluded.target_message,
                actor_message=excluded.actor_message,
                speech_blocked_by_gag=excluded.speech_blocked_by_gag,
                requires_mobile_actor=excluded.requires_mobile_actor,
                can_move_disabled_target=excluded.can_move_disabled_target,
                pregnancy_risk=excluded.pregnancy_risk
            """,
            (
                template["key"],
                template["category"],
                template["target_required"],
                template["requires_consent"],
                template["adult"],
                template["mechanical"],
                template["self_message"],
                template["room_message"],
                template["target_message"],
                template["actor_message"],
                template["speech_blocked_by_gag"],
                template["requires_mobile_actor"],
                template["can_move_disabled_target"],
                template["pregnancy_risk"],
            ),
        )


def list_socials(cursor, username, category=None):
    categories = sorted(CONSENT_CATEGORIES) if category == "all" else visible_categories(cursor, username)
    if category and category != "all":
        normalized = normalize_key(category)
        if normalized not in CONSENT_CATEGORIES:
            raise ValueError(f"Unknown social category: {category}")
        categories = {normalized}
    rows = cursor.execute(
        """
        SELECT social_key, category, requires_consent, adult, mechanical
               , pregnancy_risk
        FROM social_templates
        ORDER BY category, social_key
        """
    ).fetchall()
    return [row for row in rows if row["category"] in categories]


def social_template(cursor, social_key):
    return cursor.execute(
        "SELECT * FROM social_templates WHERE social_key=?",
        (normalize_key(social_key),),
    ).fetchone()


def visible_categories(cursor, username):
    categories = set(DEFAULT_VISIBLE_CATEGORIES)
    for category in ADULT_CATEGORIES:
        if _category_allowed(cursor, username, category):
            categories.add(category)
    return categories


def consent_summary(cursor, username):
    rows = cursor.execute(
        """
        SELECT scope, target, decision
        FROM social_consent
        WHERE username=?
        ORDER BY scope, target
        """,
        (username,),
    ).fetchall()
    states = {category: "off" for category in sorted(CONSENT_CATEGORIES)}
    players = []
    for row in rows:
        if row["target"]:
            players.append(f"{row['target']}: {row['decision']} {row['scope']}")
        else:
            states[row["scope"]] = "on" if row["decision"] == CONSENT_ALLOW else "off"
    return states, players


def set_consent(cursor, username, scope, decision, target=""):
    scope = normalize_key(scope)
    decision = normalize_key(decision)
    target = target.strip()
    if scope not in CONSENT_CATEGORIES:
        raise ValueError(f"Unknown consent category: {scope}")
    if decision not in {CONSENT_ALLOW, CONSENT_DENY}:
        raise ValueError("Consent decision must be allow or deny.")
    cursor.execute(
        """
        INSERT INTO social_consent (username, scope, target, decision, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username, scope, target) DO UPDATE SET
            decision=excluded.decision,
            updated_at=excluded.updated_at
        """,
        (username, scope, target, decision, _now()),
    )
    cursor.connection.commit()


def revoke_consent(cursor, username, target):
    target = target.strip()
    if not target:
        raise ValueError("Target is required.")
    cursor.execute(
        "DELETE FROM social_consent WHERE username=? AND target=?",
        (username, target),
    )
    clear_social_states(cursor, username, target)
    cursor.connection.commit()


def has_consent(cursor, actor_username, target_username, category, mechanical=""):
    category = normalize_key(category)
    mechanical = _mechanical_consent_scope(mechanical)
    if _player_decision(cursor, target_username, actor_username, category) == CONSENT_DENY:
        return False
    if mechanical and _player_decision(cursor, target_username, actor_username, mechanical) == CONSENT_DENY:
        return False
    if _player_decision(cursor, target_username, actor_username, category) == CONSENT_ALLOW:
        return True
    if mechanical and _player_decision(cursor, target_username, actor_username, mechanical) == CONSENT_ALLOW:
        return True
    return _category_allowed(cursor, target_username, category) and (
        not mechanical or _category_allowed(cursor, target_username, mechanical)
    )


def _mechanical_consent_scope(mechanical):
    mechanical = normalize_key(mechanical)
    if not mechanical:
        return ""
    if mechanical in MOVEMENT_STATE_TYPES:
        return "mechanical"
    if mechanical in {STATE_RESTRAINED, STATE_GAGGED, STATE_BLINDFOLDED}:
        return "restrictive"
    return mechanical


def create_social_state(cursor, state_type, actor, target, metadata=None):
    if not state_type:
        return
    if state_type == STATE_HOLD_HANDS:
        clear_social_state(cursor, STATE_HOLD_HANDS, actor, target)
        clear_social_state(cursor, STATE_HOLD_HANDS, target, actor)
    if state_type in {STATE_RESTRAINED, STATE_GAGGED, STATE_BLINDFOLDED}:
        cursor.execute(
            "DELETE FROM social_states WHERE state_type=? AND target=?",
            (state_type, target),
        )
    cursor.execute(
        """
        INSERT INTO social_states (state_type, actor, target, metadata)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(state_type, actor, target) DO UPDATE SET metadata=excluded.metadata
        """,
        (state_type, actor, target, json.dumps(metadata or {})),
    )


def clear_social_state(cursor, state_type, actor, target):
    cursor.execute(
        "DELETE FROM social_states WHERE state_type=? AND actor=? AND target=?",
        (state_type, actor, target),
    )


def clear_social_states(cursor, username, other=""):
    if other:
        cursor.execute(
            """
            DELETE FROM social_states
            WHERE (actor=? AND target=?) OR (actor=? AND target=?)
            """,
            (username, other, other, username),
        )
        return
    cursor.execute(
        "DELETE FROM social_states WHERE actor=? OR target=?",
        (username, username),
    )


def active_social_states(cursor, username):
    return cursor.execute(
        """
        SELECT state_type, actor, target, metadata, created_at
        FROM social_states
        WHERE actor=? OR target=?
        ORDER BY created_at, state_type
        """,
        (username, username),
    ).fetchall()


def movement_block(cursor, username):
    rows = cursor.execute(
        "SELECT state_type, actor FROM social_states WHERE state_type IN (?, ?, ?) AND target=?",
        (STATE_RESTRAINED, STATE_GAGGED, STATE_BLINDFOLDED, username),
    ).fetchone()
    if rows and rows["state_type"] == STATE_RESTRAINED:
        return f"You are restrained by {rows['actor']}. Use resist or ask them to free you."
    return ""


def speech_block(cursor, username):
    row = cursor.execute(
        "SELECT actor FROM social_states WHERE state_type=? AND target=? LIMIT 1",
        (STATE_GAGGED, username),
    ).fetchone()
    if row:
        return f"You are gagged by {row['actor']} and cannot speak clearly."
    return ""


def sight_block(cursor, username):
    row = cursor.execute(
        "SELECT actor FROM social_states WHERE state_type=? AND target=? LIMIT 1",
        (STATE_BLINDFOLDED, username),
    ).fetchone()
    if row:
        return f"You are blindfolded by {row['actor']}."
    return ""


def move_social_followers(actor, direction, world_map, players_by_location, from_location=None):
    rows = actor.cursor.execute(
        """
        SELECT target, state_type
        FROM social_states
        WHERE state_type IN ('holdhands', 'carry', 'support', 'guide', 'drag', 'escort') AND actor=?
        ORDER BY created_at
        """,
        (actor.username,),
    ).fetchall()
    if not rows:
        return []

    moved = []
    expected_location = from_location or coordinate_key(actor.x, actor.y)
    for row in rows:
        follower = _online_player(players_by_location, row["target"])
        if not follower:
            clear_social_state(actor.cursor, row["state_type"], actor.username, row["target"])
            actor.cursor.connection.commit()
            continue
        if coordinate_key(follower.x, follower.y) != coordinate_key(*expected_location):
            clear_social_state(actor.cursor, row["state_type"], actor.username, follower.username)
            actor.cursor.connection.commit()
            continue
        try:
            new_x, new_y = destination_for(follower.x, follower.y, direction)
            if not is_within_bounds(world_map, new_x, new_y):
                continue
            relocate_player(
                follower,
                new_x,
                new_y,
                players_by_location,
                f"{follower.username} follows {actor.username}.",
                f"{follower.username} arrives with {actor.username}.",
            )
        except LocationPersistenceError:
            continue
        moved.append(follower.username)
        verb = "leads" if row["state_type"] == STATE_HOLD_HANDS else "moves"
        follower.sendLine(f"{actor.username} {verb} you {direction}.".encode("utf-8"))
    return moved


def can_see_social(cursor, username, template):
    if not template:
        return False
    if not template["adult"]:
        return True
    return template["category"] in visible_categories(cursor, username)


def format_social_message(template, kind, actor, target=None):
    message = template[kind] if kind in template.keys() else ""
    if not message:
        return ""
    target_name = target.username if target else ""
    return sanitize_player_text(message.format(actor=actor.username, target=target_name))


def normalize_key(value):
    return str(value or "").strip().lower().replace(" ", "")


def _category_allowed(cursor, username, category):
    decision = cursor.execute(
        """
        SELECT decision
        FROM social_consent
        WHERE username=? AND scope=? AND target=''
        """,
        (username, category),
    ).fetchone()
    return bool(decision and decision["decision"] == CONSENT_ALLOW)


def _player_decision(cursor, username, actor_username, scope):
    row = cursor.execute(
        """
        SELECT decision
        FROM social_consent
        WHERE username=? AND scope=? AND target=?
        """,
        (username, scope, actor_username),
    ).fetchone()
    return row["decision"] if row else ""


def _online_player(players_by_location, username):
    for bucket in players_by_location.values():
        for player in bucket:
            if player.username.casefold() == username.casefold():
                return player
    return None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
