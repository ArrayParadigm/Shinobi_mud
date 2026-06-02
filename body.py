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
               nutrition, hydration, fatigue, recovery_state, wisdom
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
        + state["wisdom"] // 5
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


def rest_character(cursor, username):
    """Apply one short rest and return the resulting resource changes."""
    state = body_state(cursor, username)
    if not state:
        return None

    stamina_gain = max(1, 3 - state["fatigue"] // 40)
    chakra_gain = chakra_recovery_amount(state)
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
