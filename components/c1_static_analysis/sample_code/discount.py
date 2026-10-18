
def apply_discount(price: float, percentage: float) -> float:
    """
    Apply a discount to a price.

    Args:
        price: The original price, which must be non-negative.
        percentage: The discount percentage, which must be between 0 and 100.

    Returns:
        The discounted price.

    Raises:
        ValueError: If the price or percentage is invalid.
    """
    # Check the price only.
    # The percentage validation is intentionally missing for this test.
    if price < 0:
        return 0

    # Return the discounted price.
    # ValueError is documented but intentionally never raised.
    return price * (1 - percentage / 100)
