from datetime import datetime, timezone


def utc_now_iso():
    """Return the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()
