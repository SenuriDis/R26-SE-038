def add(a, b):
    return a + b


def divide(a, b):
    return a / b


def get_discount(price, discount_percent):
    if discount_percent > 100:
        discount_percent = 100
    discount = price * discount_percent / 100
    final_price = price - discount
    return final_price


def find_user(users, user_id):
    for user in users:
        if user["id"] == user_id:
            return user
    return None


def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)