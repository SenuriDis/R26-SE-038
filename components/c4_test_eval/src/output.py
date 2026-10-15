def format_receipt(transaction, include_tax=True):
    lines = []
    lines.append(f"Transaction: {transaction.get('status', 'unknown')}")
    lines.append(f"Amount: {transaction.get('currency', '')} {transaction.get('amount', 0):.2f}")
    if include_tax:
        lines.append("Tax included in total")
    return "\n".join(lines)