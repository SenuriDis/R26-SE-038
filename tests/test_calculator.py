import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# pyrefly: ignore [missing-import]
from calculator import add, subtract, multiply, divide, is_even, factorial


# Addition Tests

def test_add_positive_numbers():
    assert add(3, 5) == 8

def test_add_negative_numbers():
    assert add(-2, -3) == -5

def test_add_zero():
    assert add(0, 0) == 0

def test_add_float():
    assert add(1.5, 2.5) == 4.0


# Subtraction Tests

def test_subtract_positive():
    assert subtract(10, 4) == 6

def test_subtract_negative_result():
    assert subtract(3, 7) == -4

def test_subtract_zero():
    assert subtract(5, 0) == 5


# Multiplication Tests

def test_multiply_positive():
    assert multiply(4, 5) == 20

def test_multiply_by_zero():
    assert multiply(100, 0) == 0

def test_multiply_negatives():
    assert multiply(-3, -4) == 12


# Division Tests

def test_divide_positive():
    assert divide(10, 2) == 5.0

def test_divide_float_result():
    assert divide(7, 2) == 3.5

def test_divide_by_zero_raises():
    with pytest.raises(ValueError, match="Division by zero"):
        divide(5, 0)


# Is Even Tests

def test_is_even_true():
    assert is_even(4) is True

def test_is_even_false():
    assert is_even(7) is False

def test_is_even_zero():
    assert is_even(0) is True


# Factorial Tests

def test_factorial_zero():
    assert factorial(0) == 1

def test_factorial_positive():
    assert factorial(5) == 120

def test_factorial_one():
    assert factorial(1) == 1

def test_factorial_negative_raises():
    with pytest.raises(ValueError, match="negative"):
        factorial(-1)