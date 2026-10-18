
def calculate_late_fee(days):
    """
    Calculate the late fee for overdue days.

    Args:
        days: must be >= 0

    Returns:
        The fee amount.

    Raises:
        ValueError: If days is negative.
    """
    if days < 0:
        raise ValueError("Days cannot be negative")
    return days * 2.5


def reset_session_cache():
    """Reset the session cache."""
    pass
