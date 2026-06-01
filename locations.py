"""Coordinate-first world location helpers."""

import sqlite3


DIRECTION_OFFSETS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}


class LocationPersistenceError(RuntimeError):
    """Raised when a location change cannot be saved."""


def coordinate_key(x, y):
    """Return the canonical key used for player tracking and overlays."""
    return int(x), int(y)


def is_within_bounds(world_map, x, y):
    """Return whether a coordinate exists on the terrain map."""
    return bool(world_map) and 0 <= y < len(world_map) and 0 <= x < len(world_map[y])


def get_location(world_map, x, y, overlays=None):
    """Return terrain plus optional authored-content metadata for a coordinate."""
    if not is_within_bounds(world_map, x, y):
        return None

    key = coordinate_key(x, y)
    overlay = (overlays or {}).get(key)
    return {
        "coordinates": key,
        "terrain": world_map[y][x],
        "overlay": overlay,
    }


def destination_for(x, y, direction):
    """Return the neighboring coordinate for a cardinal direction."""
    if direction not in DIRECTION_OFFSETS:
        raise ValueError(f"Unknown direction: {direction}")
    dx, dy = DIRECTION_OFFSETS[direction]
    return coordinate_key(x + dx, y + dy)


def move_player(player, direction, world_map, players_by_location):
    """Move and persist a player while keeping tracking buckets synchronized."""
    new_x, new_y = destination_for(player.x, player.y, direction)
    if not is_within_bounds(world_map, new_x, new_y):
        return False

    old_key = coordinate_key(player.x, player.y)
    new_key = coordinate_key(new_x, new_y)
    try:
        player.cursor.execute(
            "UPDATE players SET x=?, y=? WHERE username=?",
            (new_x, new_y, player.username),
        )
        player.cursor.connection.commit()
    except sqlite3.OperationalError as exc:
        player.cursor.connection.rollback()
        raise LocationPersistenceError("Unable to save player location.") from exc

    broadcast_at(
        players_by_location,
        old_key,
        f"{player.username} leaves {direction}.",
        exclude=player,
    )
    _remove_from_bucket(player, players_by_location, old_key)

    player.x, player.y = new_key
    players_by_location.setdefault(new_key, []).append(player)
    broadcast_at(
        players_by_location,
        new_key,
        f"{player.username} arrives.",
        exclude=player,
    )
    return True


def track_player(player, players_by_location):
    """Add a player to their current coordinate bucket."""
    key = coordinate_key(player.x, player.y)
    bucket = players_by_location.setdefault(key, [])
    if player not in bucket:
        bucket.append(player)


def untrack_player(player, players_by_location):
    """Remove a player from their current coordinate bucket."""
    _remove_from_bucket(player, players_by_location, coordinate_key(player.x, player.y))


def players_at(players_by_location, x, y, exclude=None):
    """Return tracked players at a coordinate."""
    return [
        player
        for player in players_by_location.get(coordinate_key(x, y), [])
        if player is not exclude
    ]


def online_players(players_by_location):
    """Return each tracked player once, ordered by username."""
    unique_players = {
        id(player): player
        for bucket in players_by_location.values()
        for player in bucket
    }
    return sorted(unique_players.values(), key=lambda player: player.username.lower())


def broadcast_at(players_by_location, location, message, exclude=None):
    """Send a message to tracked players at a coordinate."""
    for recipient in players_by_location.get(location, []):
        if recipient is not exclude:
            recipient.sendLine(message.encode("utf-8"))


def _remove_from_bucket(player, players_by_location, key):
    bucket = players_by_location.get(key)
    if not bucket or player not in bucket:
        return
    bucket.remove(player)
    if not bucket:
        del players_by_location[key]
