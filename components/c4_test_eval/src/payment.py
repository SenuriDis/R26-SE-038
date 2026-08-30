def process_transaction(amount, currency, user_id, payment_method, discount=None):
    if not isinstance(amount, (int, float)):
        raise TypeError("Amount must be numeric")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    if currency not in ["USD", "EUR", "GBP", "LKR"]:
        raise ValueError(f"Unsupported currency: {currency}")

    if discount is not None:
        if not 0 <= discount <= 100:
            raise ValueError("Discount must be between 0 and 100")
        amount = amount - (amount * discount / 100)

    tax_rate = 0.15 if currency == "USD" else 0.20
    tax = amount * tax_rate
    total = amount + tax

    for attempt in range(3):
        if payment_method == "card":
            result = _charge_card(user_id, total, currency)
        elif payment_method == "wallet":
            result = _charge_wallet(user_id, total)
        else:
            raise ValueError(f"Unknown payment method: {payment_method}")

        if result:
            return {
                "status": "success",
                "amount": round(total, 2),
                "currency": currency,
                "attempts": attempt + 1,
            }

    return {"status": "failed", "amount": total, "currency": currency}


def _charge_card(user_id, amount, currency):
    return True


def _charge_wallet(user_id, amount):
    return True


def validate_payment(amount, currency, user_id):
    if not amount or amount <= 0:
        return False, "Invalid amount"
    if not currency:
        return False, "Currency required"
    if not user_id:
        return False, "User ID required"
    return True, "Valid"