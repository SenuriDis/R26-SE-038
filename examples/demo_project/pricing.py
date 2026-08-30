"""
Order pricing rules.

Deliberately small, and written to exercise every stage of the pipeline:

  - Google-style docstrings, so C1's requirement analysis can extract a
    contract (parameter constraints, declared exceptions).
  - `apply_discount` carries a planted bug, so C3's generated tests should
    fail against it and C4 should classify that failure as a Real Defect.
  - `charge` documents a `ValueError` it never raises, so C1's gap detector
    should flag missing exception handling.
"""


def apply_discount(price, percent):
    """Apply a percentage discount to a price.

    Args:
        price: Original price. Must be greater than 0.
        percent: Discount to apply, from 0 to 100.

    Returns:
        The discounted price.

    Raises:
        ValueError: If price is not positive.
        ValueError: If percent is outside 0 to 100.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")

    # BUG (planted): percent is a percentage, so this should divide by 100.
    # 20% off 100 should be 80, but this returns 100 * (1 - 20) = -1900.
    return price * (1 - percent)


def shipping_cost(weight_kg, express=False):
    """Work out shipping cost from parcel weight.

    Args:
        weight_kg: Parcel weight in kilograms. Must be greater than 0.
        express: Whether to use express delivery.

    Returns:
        Shipping cost as a float.

    Raises:
        ValueError: If weight_kg is not positive.
    """
    if weight_kg <= 0:
        raise ValueError("weight must be positive")

    if weight_kg <= 1:
        base = 3.0
    elif weight_kg <= 5:
        base = 6.5
    else:
        base = 6.5 + (weight_kg - 5) * 1.2

    return round(base * 2 if express else base, 2)


def charge(amount, balance):
    """Take an amount from a balance.

    Args:
        amount: Amount to charge. Must not exceed balance.
        balance: Funds available.

    Returns:
        The remaining balance.

    Raises:
        ValueError: If amount exceeds balance.
    """
    # NOTE: the docstring promises a ValueError, but nothing raises one.
    # C1's gap detector should report missing exception handling here.
    return balance - amount
