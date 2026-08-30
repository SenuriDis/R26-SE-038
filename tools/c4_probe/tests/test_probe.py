"""
Each failing test here should land in a different C4 category.

  test_real_defect        -> "Real Defect"          (correct test, buggy code)
  test_invalid_ai_test    -> "Invalid AI Test"      (test itself is wrong)
  test_environment_failure-> "Environment Failure"  (missing dependency)
  test_passes             -> passes, as a control
"""

import pytest

from sample import add, apply_discount, classify, divide


def test_passes():
    """Control: this must pass."""
    assert add(2, 3) == 5
    assert classify(-1) == "negative"
    assert divide(10, 2) == 5


def test_real_defect():
    """
    Correct expectation, buggy implementation.

    20% off 100 should be 80. apply_discount computes 100 * (1 - 20) = -1900.
    The test is right; the code is wrong -> Real Defect.
    """
    assert apply_discount(100, 20) == 80


def test_invalid_ai_test():
    """
    The test itself is malformed -- calls a function that does not exist.
    Nothing wrong with the source -> Invalid AI Test.
    """
    from sample import add as _add
    assert _add.nonexistent_attribute == 1


def test_environment_failure():
    """A dependency that is not installed -> Environment Failure."""
    import definitely_not_a_real_package_xyz  # noqa: F401

    assert True
