import logging

from content import create_authored_content_tables
from combat import create_combat_tables, ensure_stance_columns, retire_initial_stance_placeholders
from body import ensure_body_columns
from items import create_item_tables, ensure_item_seed_tracking
from npcs import create_npc_tables
from socials import create_social_tables
from techniques import (
    create_technique_tables,
    ensure_catalog_availability_columns,
    ensure_jutsu_execution_columns,
    ensure_usage_progress_columns,
)


PLAYER_COLUMNS = (
    "id",
    "username",
    "password",
    "x",
    "y",
    "is_admin",
    "is_builder",
    "role_type",
    "health",
    "stamina",
    "chakra",
    "strength",
    "dexterity",
    "agility",
    "intelligence",
    "wisdom",
    "dojo_alignment",
    "max_health",
    "max_stamina",
    "max_chakra",
    "clan",
    "natural_release",
    "nutrition",
    "hydration",
    "fatigue",
    "recovery_state",
    "description",
    "created_at",
    "last_login_at",
)


def create_players_table(cursor, table_name="players"):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT NOT NULL,
            x INTEGER DEFAULT 500,
            y INTEGER DEFAULT 500,
            is_admin BOOLEAN DEFAULT 0,
            is_builder BOOLEAN DEFAULT 0,
            role_type TEXT DEFAULT 'newbie',
            health INTEGER DEFAULT 10,
            stamina INTEGER DEFAULT 10,
            chakra INTEGER DEFAULT 10,
            strength INTEGER DEFAULT 10,
            dexterity INTEGER DEFAULT 10,
            agility INTEGER DEFAULT 10,
            intelligence INTEGER DEFAULT 10,
            wisdom INTEGER DEFAULT 10,
            dojo_alignment TEXT DEFAULT 'None',
            max_health INTEGER DEFAULT 10,
            max_stamina INTEGER DEFAULT 10,
            max_chakra INTEGER DEFAULT 10,
            clan TEXT DEFAULT 'Unaffiliated',
            natural_release TEXT DEFAULT 'Undeclared',
            nutrition INTEGER NOT NULL DEFAULT 100,
            hydration INTEGER NOT NULL DEFAULT 100,
            fatigue INTEGER NOT NULL DEFAULT 0,
            recovery_state TEXT NOT NULL DEFAULT 'ready',
            description TEXT NOT NULL DEFAULT 'An undescribed shinobi stands here.',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        )
        """
    )


def migration_001_non_admin_default(cursor):
    """Rebuild legacy player tables so new accounts default to non-admin."""
    columns = cursor.execute("PRAGMA table_info(players)").fetchall()
    is_admin = next((column for column in columns if column[1] == "is_admin"), None)
    if is_admin and str(is_admin[4]).strip("'\"") == "0":
        return

    legacy_columns = {column[1] for column in columns}
    copied_columns = [column for column in PLAYER_COLUMNS if column in legacy_columns]

    cursor.execute("ALTER TABLE players RENAME TO players_legacy")
    create_players_table(cursor)
    if copied_columns:
        names = ", ".join(copied_columns)
        cursor.execute(f"INSERT INTO players ({names}) SELECT {names} FROM players_legacy")
    cursor.execute("DROP TABLE players_legacy")


def migration_002_persistent_items(cursor):
    """Add persistent room objects and character inventories."""
    create_item_tables(cursor)


def migration_003_authored_content_and_npcs(cursor):
    """Track authored imports and add persistent NPC state."""
    create_item_tables(cursor)
    ensure_item_seed_tracking(cursor)
    create_authored_content_tables(cursor)
    create_npc_tables(cursor)


def migration_004_npc_combat_state(cursor):
    """Add authored NPC combat tuning and live health state."""
    create_npc_tables(cursor)


def ensure_player_foundation_columns(cursor):
    """Add durable character identity and maximum resource fields."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    for column_name, definition in (
        ("max_health", "INTEGER DEFAULT 10"),
        ("max_stamina", "INTEGER DEFAULT 10"),
        ("max_chakra", "INTEGER DEFAULT 10"),
        ("clan", "TEXT DEFAULT 'Unaffiliated'"),
        ("natural_release", "TEXT DEFAULT 'Undeclared'"),
    ):
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {column_name} {definition}")
    cursor.execute("UPDATE players SET max_health=health WHERE max_health IS NULL OR max_health < health")
    cursor.execute("UPDATE players SET max_stamina=stamina WHERE max_stamina IS NULL OR max_stamina < stamina")
    cursor.execute("UPDATE players SET max_chakra=chakra WHERE max_chakra IS NULL OR max_chakra < chakra")
    if "role_type" in columns:
        cursor.execute(
            "UPDATE players SET role_type='newbie' "
            "WHERE role_type IS NULL OR role_type=0 OR role_type='0'"
        )
        cursor.execute("UPDATE players SET role_type='Ninjutsu' WHERE role_type='a'")
        cursor.execute("UPDATE players SET role_type='Genjutsu' WHERE role_type='b'")
        cursor.execute("UPDATE players SET role_type='Taijutsu' WHERE role_type='c'")


def ensure_builder_access_column(cursor):
    """Add an explicit builder-access flag separate from admin access."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    if "is_builder" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN is_builder BOOLEAN DEFAULT 0")


def ensure_player_login_columns(cursor):
    """Add non-sensitive account timestamps for admin inspection."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    if "created_at" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN created_at TEXT")
        cursor.execute("UPDATE players SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL")
    if "last_login_at" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN last_login_at TEXT")


def migration_005_inventory_and_character_foundation(cursor):
    """Add item interaction metadata, equipment, and character identity."""
    create_item_tables(cursor)
    ensure_item_seed_tracking(cursor)
    ensure_player_foundation_columns(cursor)


def migration_006_combat_reliability(cursor):
    """Add authored NPC accuracy and evasion for stat-based combat."""
    create_npc_tables(cursor)


def migration_007_body_foundation(cursor):
    """Add abstract body resources for rest and future recovery systems."""
    ensure_body_columns(cursor)


def migration_008_consumable_items(cursor):
    """Add authored food and drink restoration metadata."""
    create_item_tables(cursor)


def migration_009_skill_and_jutsu_framework(cursor):
    """Add authored technique definitions and character progression storage."""
    create_technique_tables(cursor)


def migration_010_usage_based_techniques(cursor):
    """Replace point-spend advancement with percentage progress from valid use."""
    create_technique_tables(cursor)
    ensure_usage_progress_columns(cursor)


def migration_011_technique_catalog_placeholders(cursor):
    """Separate available techniques from catalog-only placeholders."""
    create_technique_tables(cursor)
    ensure_catalog_availability_columns(cursor)


def migration_012_throwable_items(cursor):
    """Add authored ranged damage for throwable inventory items."""
    create_item_tables(cursor)


def migration_013_substitution_technique(cursor):
    """Add authored jutsu execution metadata and persisted activation state."""
    create_technique_tables(cursor)
    ensure_jutsu_execution_columns(cursor)


def migration_014_pulse_combat_engagements(cursor):
    """Add persisted pulse combat engagements, stances, and queued modifiers."""
    create_combat_tables(cursor)


def migration_015_stance_profiles(cursor):
    """Add damage reduction and retire the initial named stance prototypes."""
    create_combat_tables(cursor)
    ensure_stance_columns(cursor)
    retire_initial_stance_placeholders(cursor)


def ensure_character_identity_columns(cursor):
    """Add character identity fields that belong on player rows."""
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(players)")
    }
    if "description" not in columns:
        cursor.execute(
            "ALTER TABLE players ADD COLUMN description "
            "TEXT NOT NULL DEFAULT 'An undescribed shinobi stands here.'"
        )


def create_builder_tables(cursor):
    """Create lightweight builder safety and audit storage."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS builder_undo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            zone_file TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS builder_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            zone_file TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {
        column[1]
        for column in cursor.execute("PRAGMA table_info(builder_audit)")
    }
    if "target" not in columns:
        cursor.execute("ALTER TABLE builder_audit ADD COLUMN target TEXT NOT NULL DEFAULT ''")
    if "details" not in columns:
        cursor.execute("ALTER TABLE builder_audit ADD COLUMN details TEXT NOT NULL DEFAULT ''")


def ensure_technique_point_columns(cursor):
    """Add hidden point progress while preserving visible percentage columns."""
    create_technique_tables(cursor)
    for table_name in ("character_skills", "character_jutsus"):
        columns = {
            column[1]
            for column in cursor.execute(f"PRAGMA table_info({table_name})")
        }
        if "progress_points" not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN progress_points INTEGER NOT NULL DEFAULT 0"
            )
            if "progress_percent" in columns:
                cursor.execute(
                    f"""
                    UPDATE {table_name}
                    SET progress_points=CASE
                        WHEN progress_percent >= 100 THEN 100000
                        ELSE MAX(0, progress_percent * 1000)
                    END
                    """
                )


def migration_016_character_identity_and_builder_safety(cursor):
    """Add character descriptions and builder undo/audit storage."""
    ensure_character_identity_columns(cursor)
    create_builder_tables(cursor)


def migration_017_technique_progress_points(cursor):
    """Add hidden point-based skill and jutsu progress."""
    ensure_technique_point_columns(cursor)


def migration_018_builder_publish_audit_columns(cursor):
    """Expand builder audit records for publish and destructive-edit tracking."""
    create_builder_tables(cursor)


def migration_019_builder_access_flag(cursor):
    """Add in-game builder access delegation separate from admin access."""
    ensure_builder_access_column(cursor)


def migration_020_rich_item_npc_templates(cursor):
    """Add richer authored item and NPC template metadata."""
    create_item_tables(cursor)
    create_npc_tables(cursor)


def migration_021_player_login_timestamps(cursor):
    """Add non-sensitive player account timestamps for admin inspection."""
    ensure_player_login_columns(cursor)


def migration_022_combat_techniques(cursor):
    """Add authored stamina-based combat techniques and queue effects."""
    create_combat_tables(cursor)


def migration_023_npc_stat_sheets_and_round_combat(cursor):
    """Add player-like NPC stats/resources and precise combat round timing."""
    create_npc_tables(cursor)
    create_combat_tables(cursor)


def migration_024_social_catalog_and_consent(cursor):
    """Add catalog-backed socials, consent settings, and active social states."""
    create_social_tables(cursor)


MIGRATIONS = (
    (1, migration_001_non_admin_default),
    (2, migration_002_persistent_items),
    (3, migration_003_authored_content_and_npcs),
    (4, migration_004_npc_combat_state),
    (5, migration_005_inventory_and_character_foundation),
    (6, migration_006_combat_reliability),
    (7, migration_007_body_foundation),
    (8, migration_008_consumable_items),
    (9, migration_009_skill_and_jutsu_framework),
    (10, migration_010_usage_based_techniques),
    (11, migration_011_technique_catalog_placeholders),
    (12, migration_012_throwable_items),
    (13, migration_013_substitution_technique),
    (14, migration_014_pulse_combat_engagements),
    (15, migration_015_stance_profiles),
    (16, migration_016_character_identity_and_builder_safety),
    (17, migration_017_technique_progress_points),
    (18, migration_018_builder_publish_audit_columns),
    (19, migration_019_builder_access_flag),
    (20, migration_020_rich_item_npc_templates),
    (21, migration_021_player_login_timestamps),
    (22, migration_022_combat_techniques),
    (23, migration_023_npc_stat_sheets_and_round_combat),
    (24, migration_024_social_catalog_and_consent),
)


def apply_migrations(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row[0]
        for row in cursor.execute("SELECT version FROM schema_migrations").fetchall()
    }

    for version, migration in MIGRATIONS:
        if version in applied:
            continue
        logging.info("Applying database migration %s.", version)
        migration(cursor)
        cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    connection.commit()
