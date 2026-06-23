"""Module jwt_service.py."""
import logging
from datetime import datetime, timezone

import app.extensions as ext

logger = logging.getLogger('app')

BLACKLIST_PREFIX = "jti:blacklist:"


def blacklist_token(jti: str, exp: int) -> None:
    """
    Store jti in Redis until it naturally expires.

    Args:
        jti: Unique JWT ID from the token claims.
        exp: Token expiry as Unix timestamp (from JWT 'exp' claim).
    """
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = exp - now

    if ttl <= 0:
        return

    key = f"{BLACKLIST_PREFIX}{jti}"
    ext.redis_client.setex(name=key, time=ttl, value="1")
    logger.info(f"🚫 Blacklisted jti={jti} for {ttl}s")


def is_blacklisted(jti: str) -> bool:
    """Returns True if this jti has been blacklisted (i.e. logged out)."""
    return ext.redis_client.exists(f"{BLACKLIST_PREFIX}{jti}") == 1
