"""Lineage and offspring scaffolding for Veilborn characters."""

from essences import compatible_for_lineage


def lineage_allowed(parent_a_essence, parent_b_essence):
    """Return whether two essence states can produce lineage in the current rules."""
    return compatible_for_lineage(parent_a_essence, parent_b_essence)
