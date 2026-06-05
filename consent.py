"""Consent management facade for social and adult-only mechanics."""

from socials import (
    CONSENT_ALLOW,
    CONSENT_DENY,
    consent_summary,
    has_consent,
    revoke_consent,
    set_consent,
)


__all__ = [
    "CONSENT_ALLOW",
    "CONSENT_DENY",
    "consent_summary",
    "has_consent",
    "revoke_consent",
    "set_consent",
]
