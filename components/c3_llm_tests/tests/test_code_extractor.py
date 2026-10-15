"""
tests/test_code_extractor.py
──────────────────────────────
Regression tests for CodeExtractor's AST-based extraction, covering two bugs
found while integrating Component 3 with Component 2's ML risk report:

1. Function-name collisions across classes/functions in the same file used
   to silently return the FIRST AST match, ignoring the (start_line,
   end_line) hint that Component 2 provides — so a risky method could be
   swapped out for an unrelated same-named one with no error raised.
2. Decorated functions/methods used to lose their decorator line(s), since
   `FunctionDef.lineno` points at the `def` line, not the decorator, as of
   Python 3.8.

Run with: python -m pytest tests/test_code_extractor.py -v
"""

import pytest

from src.utils.code_extractor import CodeExtractor


COLLISION_SOURCE = '''\
class PaymentProcessorA:
    def process(self, x):
        return x + 1


class PaymentProcessorB:
    @staticmethod
    def process(y):
        return y * 2
'''


@pytest.fixture
def collision_repo(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "payment.py").write_text(COLLISION_SOURCE, encoding="utf-8")
    return tmp_path


def test_disambiguates_by_line_hint_picks_second_candidate(collision_repo):
    """Given PaymentProcessorB.process's line range, extraction must return
    B's implementation, not silently fall back to A's (the first AST match)."""
    extractor = CodeExtractor(str(collision_repo))

    result = extractor.extract(
        file_path="src/payment.py",
        function_name="process",
        start_line=7,
        end_line=8,
    )

    assert "return y * 2" in result
    assert "return x + 1" not in result


def test_disambiguates_by_line_hint_picks_first_candidate(collision_repo):
    """Given PaymentProcessorA.process's line range, extraction must return
    A's implementation, not B's."""
    extractor = CodeExtractor(str(collision_repo))

    result = extractor.extract(
        file_path="src/payment.py",
        function_name="process",
        start_line=2,
        end_line=3,
    )

    assert "return x + 1" in result
    assert "return y * 2" not in result


def test_preserves_decorator_line(collision_repo):
    """The @staticmethod decorator must be included in the extracted
    source, not dropped."""
    extractor = CodeExtractor(str(collision_repo))

    result = extractor.extract(
        file_path="src/payment.py",
        function_name="process",
        start_line=7,
        end_line=8,
    )

    assert "@staticmethod" in result


def test_no_line_hint_falls_back_to_first_ast_match(collision_repo):
    """When no line hint is available (e.g. a caller other than the ML
    report path), extraction degrades gracefully to the old first-match
    behaviour instead of raising."""
    extractor = CodeExtractor(str(collision_repo))
    source = (collision_repo / "src" / "payment.py").read_text(encoding="utf-8")

    result = extractor._extract_by_ast(source, "process")

    assert "return x + 1" in result
