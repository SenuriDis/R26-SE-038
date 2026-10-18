
def calculate_fee(amount: float, rate: float) -> float:
    """
    Calculate a fee based on the amount and rate.

    Args:
        amount: The amount to calculate the fee for.
        rate: The fee rate, which must be non-negative.

    Returns:
        The calculated fee.

    Raises:
        ValueError: If the amount or rate is negative.
    """
    if amount < 0 or rate < 0:
        raise ValueError("Amount and rate must be non-negative")

    return amount * rate


def undocumented_helper(value):
    return value * 2
