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


DEFAULT_SOCIALS = (
    {
        "key": "wave",
        "category": "normal",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "You wave.",
        "room_message": "{actor} waves.",
        "target_message": "",
        "actor_message": "",
    },
    {
        "key": "smile",
        "category": "normal",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "You smile.",
        "room_message": "{actor} smiles.",
        "target_message": "",
        "actor_message": "",
    },
    {
        "key": "nod",
        "category": "normal",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "You nod.",
        "room_message": "{actor} nods.",
        "target_message": "",
        "actor_message": "",
    },
    {
        "key": "bow",
        "category": "normal",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "You bow.",
        "room_message": "{actor} bows.",
        "target_message": "",
        "actor_message": "",
    },
    {
        "key": "laugh",
        "category": "normal",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "You laugh.",
        "room_message": "{actor} laughs.",
        "target_message": "",
        "actor_message": "",
    },
    {
        "key": "hug",
        "category": "friendly",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 0,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} hugs {target}.",
        "target_message": "{actor} hugs you.",
        "actor_message": "You hug {target}.",
    },
    {
        "key": "highfive",
        "category": "friendly",
        "target_required": 1,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} high-fives {target}.",
        "target_message": "{actor} high-fives you.",
        "actor_message": "You high-five {target}.",
    },
    {
        "key": "pat",
        "category": "playful",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 0,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} gives {target} a playful pat.",
        "target_message": "{actor} gives you a playful pat.",
        "actor_message": "You give {target} a playful pat.",
    },
    {
        "key": "poke",
        "category": "playful",
        "target_required": 1,
        "requires_consent": 0,
        "adult": 0,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} pokes {target}.",
        "target_message": "{actor} pokes you.",
        "actor_message": "You poke {target}.",
    },
    {
        "key": "cuddle",
        "category": "intimate",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 1,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} cuddles close with {target}.",
        "target_message": "{actor} cuddles close with you.",
        "actor_message": "You cuddle close with {target}.",
    },
    {
        "key": "nuzzle",
        "category": "intimate",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 1,
        "mechanical": "",
        "self_message": "",
        "room_message": "{actor} nuzzles {target}.",
        "target_message": "{actor} nuzzles you.",
        "actor_message": "You nuzzle {target}.",
    },
    {
        "key": "holdhands",
        "category": "utility",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 0,
        "mechanical": STATE_HOLD_HANDS,
        "self_message": "",
        "room_message": "{actor} takes {target}'s hand.",
        "target_message": "{actor} takes your hand.",
        "actor_message": "You take {target}'s hand.",
    },
    {
        "key": "tie",
        "category": "bdsm",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 1,
        "mechanical": STATE_RESTRAINED,
        "self_message": "",
        "room_message": "{actor} restrains {target}.",
        "target_message": "{actor} restrains you.",
        "actor_message": "You restrain {target}.",
    },
    {
        "key": "restrain",
        "category": "bdsm",
        "target_required": 1,
        "requires_consent": 1,
        "adult": 1,
        "mechanical": STATE_RESTRAINED,
        "self_message": "",
        "room_message": "{actor} restrains {target}.",
        "target_message": "{actor} restrains you.",
        "actor_message": "You restrain {target}.",
    },
    {
        "key": "kneel",
        "category": "bdsm",
        "target_required": 0,
        "requires_consent": 0,
        "adult": 1,
        "mechanical": "",
        "self_message": "You kneel.",
        "room_message": "{actor} kneels.",
        "target_message": "",
        "actor_message": "",
    },
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
    seed_default_socials(cursor)


def seed_default_socials(cursor):
    for template in DEFAULT_SOCIALS:
        cursor.execute(
            """
            INSERT INTO social_templates (
                social_key, category, target_required, requires_consent, adult,
                mechanical, self_message, room_message, target_message, actor_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(social_key) DO UPDATE SET
                category=excluded.category,
                target_required=excluded.target_required,
                requires_consent=excluded.requires_consent,
                adult=excluded.adult,
                mechanical=excluded.mechanical,
                self_message=excluded.self_message,
                room_message=excluded.room_message,
                target_message=excluded.target_message,
                actor_message=excluded.actor_message
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


def create_social_state(cursor, state_type, actor, target, metadata=None):
    if not state_type:
        return
    if state_type == STATE_HOLD_HANDS:
        clear_social_state(cursor, STATE_HOLD_HANDS, actor, target)
        clear_social_state(cursor, STATE_HOLD_HANDS, target, actor)
    if state_type == STATE_RESTRAINED:
        cursor.execute(
            "DELETE FROM social_states WHERE state_type=? AND target=?",
            (STATE_RESTRAINED, target),
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
    row = cursor.execute(
        "SELECT actor FROM social_states WHERE state_type=? AND target=? LIMIT 1",
        (STATE_RESTRAINED, username),
    ).fetchone()
    if row:
        return f"You are restrained by {row['actor']}. Use resist or ask them to release you."
    return ""


def move_social_followers(actor, direction, world_map, players_by_location, from_location=None):
    rows = actor.cursor.execute(
        """
        SELECT target
        FROM social_states
        WHERE state_type=? AND actor=?
        ORDER BY created_at
        """,
        (STATE_HOLD_HANDS, actor.username),
    ).fetchall()
    if not rows:
        return []

    moved = []
    expected_location = from_location or coordinate_key(actor.x, actor.y)
    for row in rows:
        follower = _online_player(players_by_location, row["target"])
        if not follower:
            clear_social_state(actor.cursor, STATE_HOLD_HANDS, actor.username, row["target"])
            actor.cursor.connection.commit()
            continue
        if coordinate_key(follower.x, follower.y) != coordinate_key(*expected_location):
            clear_social_state(actor.cursor, STATE_HOLD_HANDS, actor.username, follower.username)
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
        follower.sendLine(f"{actor.username} leads you {direction}.".encode("utf-8"))
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
