"""Persistent body resources and deliberate short-rest recovery."""


DEFAULT_NUTRITION = 100
DEFAULT_HYDRATION = 100
DEFAULT_FATIGUE = 0
MIN_BODY_RESOURCE = 0
MAX_BODY_RESOURCE = 100


def ensure_body_columns(cursor):
    """Add the first abstract body-resource fields to existing characters."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    for column_name, definition in (
        ("nutrition", f"INTEGER NOT NULL DEFAULT {DEFAULT_NUTRITION}"),
        ("hydration", f"INTEGER NOT NULL DEFAULT {DEFAULT_HYDRATION}"),
        ("fatigue", f"INTEGER NOT NULL DEFAULT {DEFAULT_FATIGUE}"),
        ("recovery_state", "TEXT NOT NULL DEFAULT 'ready'"),
    ):
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {column_name} {definition}")


def body_state(cursor, username):
    """Return one character's abstract body-resource state."""
    return cursor.execute(
        """
        SELECT health, max_health, stamina, max_stamina, chakra, max_chakra,
               nutrition, hydration, fatigue, recovery_state, wisdom, strength,
               intelligence, dexterity, agility
        FROM players
        WHERE username=?
        """,
        (username,),
    ).fetchone()


def chakra_recovery_amount(state):
    """Calculate chakra restored by one deliberate rest command."""
    return max(
        1,
        1
        + state["intelligence"] // 5
        + state["hydration"] // 50
        + state["nutrition"] // 50
        - state["fatigue"] // 25,
    )


def add_fatigue(cursor, username, amount):
    """Accumulate bounded fatigue inside the caller's transaction."""
    cursor.execute(
        """
        UPDATE players
        SET fatigue=MIN(?, fatigue + ?),
            recovery_state=CASE
                WHEN MIN(?, fatigue + ?) < 50 THEN 'ready'
                ELSE 'strained'
            END
        WHERE username=?
        """,
        (MAX_BODY_RESOURCE, amount, MAX_BODY_RESOURCE, amount, username),
    )


def rest_character(cursor, username, recovery_bonus=0):
    """Apply one short rest and return the resulting resource changes."""
    state = body_state(cursor, username)
    if not state:
        return None
    if state["nutrition"] <= MIN_BODY_RESOURCE:
        return {"status": "blocked", "reason": "nutrition"}
    if state["hydration"] <= MIN_BODY_RESOURCE:
        return {"status": "blocked", "reason": "hydration"}

    condition_bonus = state["wisdom"] // 10
    stamina_gain = max(1, 3 + condition_bonus + recovery_bonus - state["fatigue"] // 40)
    chakra_gain = chakra_recovery_amount(state) + recovery_bonus
    stamina = min(state["max_stamina"], state["stamina"] + stamina_gain)
    chakra = min(state["max_chakra"], state["chakra"] + chakra_gain)
    nutrition = max(MIN_BODY_RESOURCE, state["nutrition"] - 1)
    hydration = max(MIN_BODY_RESOURCE, state["hydration"] - 1)
    fatigue = max(MIN_BODY_RESOURCE, state["fatigue"] - 10)
    recovery_state = "ready" if fatigue < 50 else "strained"

    cursor.execute(
        """
        UPDATE players
        SET stamina=?, chakra=?, nutrition=?, hydration=?, fatigue=?, recovery_state=?
        WHERE username=?
        """,
        (stamina, chakra, nutrition, hydration, fatigue, recovery_state, username),
    )
    cursor.connection.commit()
    return {
        "status": "rested",
        "stamina_restored": stamina - state["stamina"],
        "chakra_restored": chakra - state["chakra"],
        "stamina": stamina,
        "max_stamina": state["max_stamina"],
        "chakra": chakra,
        "max_chakra": state["max_chakra"],
        "nutrition": nutrition,
        "hydration": hydration,
        "fatigue": fatigue,
        "recovery_state": recovery_state,
    }


def apply_vacuum_exposure(cursor, username):
    """Apply one room tick of vacuum strain."""
    state = body_state(cursor, username)
    if not state:
        return None
    fatigue_gain = max(5, 15 - state["wisdom"] // 2 - state["strength"] // 4)
    fatigue = min(MAX_BODY_RESOURCE, state["fatigue"] + fatigue_gain)
    health = state["health"]
    if fatigue >= MAX_BODY_RESOURCE:
        health = max(0, health - 1)
    recovery_state = "ready" if fatigue < 50 else "strained"
    cursor.execute(
        """
        UPDATE players
        SET fatigue=?, health=?, recovery_state=?
        WHERE username=?
        """,
        (fatigue, health, recovery_state, username),
    )
    cursor.connection.commit()
    return {"fatigue": fatigue, "health": health, "max_health": state["max_health"]}


def body_warnings(state):
    """Return concise warnings for body conditions that affect recovery."""
    warnings = []
    if state["nutrition"] <= MIN_BODY_RESOURCE:
        warnings.append("You are too hungry to recover through rest.")
    elif state["nutrition"] < 25:
        warnings.append("Low nutrition is reducing your recovery.")
    if state["hydration"] <= MIN_BODY_RESOURCE:
        warnings.append("You are too dehydrated to recover through rest.")
    elif state["hydration"] < 25:
        warnings.append("Low hydration is reducing your recovery.")
    if state["fatigue"] >= 50:
        warnings.append("High fatigue is straining your recovery.")
    return warnings
