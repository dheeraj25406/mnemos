import hashlib
import hmac
import secrets


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for secure storage."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of hashed API keys."""
    provided_hash = hash_api_key(provided_key)
    return hmac.compare_digest(provided_hash, stored_hash)


def generate_api_key(prefix: str = "mnk_live_") -> str:
    """Generate a high-entropy API key."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"
