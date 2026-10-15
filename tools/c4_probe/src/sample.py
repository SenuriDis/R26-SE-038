"""Small module with one genuine defect, for probing C4's failure classifier."""


def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ValueError("cannot divide by zero")
    return a / b


def apply_discount(price, pct):
    # Genuine defect: should be price * (1 - pct/100).
    # A correct test asserting the right answer will fail here.
    return price * (1 - pct)


def classify(n):
    if n < 0:
        return "negative"
    elif n == 0:
        return "zero"
    return "positive"
