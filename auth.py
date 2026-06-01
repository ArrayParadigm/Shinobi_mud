import hashlib
import hmac
import re
import secrets


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")
SCRYPT_PREFIX = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64


def validate_username(username):
    """Return an error message when a username is invalid."""
    if not USERNAME_PATTERN.fullmatch(username):
        return "Usernames must be 3-20 characters and use letters, numbers, or underscores. Start with a letter."
    return None


def hash_password(password):
    """Hash a password with a unique salt using scrypt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return f"{SCRYPT_PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    """Return (matches, needs_upgrade), including support for legacy SHA-256 hashes."""
    if stored_hash.startswith(f"{SCRYPT_PREFIX}$"):
        try:
            _, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(expected),
            )
            return hmac.compare_digest(actual, expected), False
        except (TypeError, ValueError):
            return False, False

    if re.fullmatch(r"[0-9a-f]{64}", stored_hash):
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash), True

    return False, False
