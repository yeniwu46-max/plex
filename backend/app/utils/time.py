"""UTC time helpers preserving the project's naive database convention."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return naive UTC for existing SQLAlchemy DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
