from datetime import datetime, timezone


def utc_now() -> datetime:
    """Naive UTC now, matching the naive DateTime columns used throughout the DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
