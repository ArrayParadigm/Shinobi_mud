"""Pregnancy and essence-gated breeding helpers."""

from character_state import maybe_apply_pregnancy as _maybe_apply_pregnancy
from essences import compatible_for_lineage


def maybe_apply_pregnancy(cursor, actor_username, target_username, risk_flag, rng=None):
    """Apply pregnancy only when current consent/biology checks and essence rules allow."""
    if not risk_flag:
        return {"pregnant": False}
    actor = cursor.execute(
        "SELECT essence FROM players WHERE username=? COLLATE NOCASE",
        (actor_username,),
    ).fetchone()
    target = cursor.execute(
        "SELECT essence FROM players WHERE username=? COLLATE NOCASE",
        (target_username,),
    ).fetchone()
    if actor and target and not compatible_for_lineage(actor["essence"], target["essence"]):
        return {"pregnant": False, "reason": "essence_incompatible"}
    return _maybe_apply_pregnancy(cursor, actor_username, target_username, risk_flag, rng=rng)
