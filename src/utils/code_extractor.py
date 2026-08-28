"""
src/utils/code_extractor.py
────────────────────────────
Extracts source code from a repository using file path and line numbers.

Component 2 gives us:
  - file_path (relative, e.g. "src/payment.py")
  - start_line (e.g. 45)
  - end_line (e.g. 78)

We combine with the repository path to read the actual source code.
"""

import ast
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CodeExtractor:
    """
    Reads source code from a repository using file path and line numbers.
    Also extracts the function name to verify we got the right code.
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(
                f"Repository not found: {self.repo_path}"
            )

    def extract(
        self,
        file_path: str,
        function_name: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """
        Extract source code for a function from the repository.

        Strategy:
        1. Try AST-based extraction first — finds the exact function
           definition regardless of line number accuracy
        2. Fall back to line-based extraction if AST fails

        Args:
            file_path: Relative path from repo root e.g. "src/payment.py"
            function_name: Name of the function to extract
            start_line: Starting line number from Component 2
            end_line: Ending line number from Component 2

        Returns:
            Source code string of the function
        """
        # Build full path
        full_path = self.repo_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(
                f"File not found: {full_path}\n"
                f"Repository: {self.repo_path}\n"
                f"Relative path: {file_path}"
            )

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
            lines = source.splitlines(keepends=True)

        # Strategy 1: AST-based extraction (preferred)
        try:
            extracted = self._extract_by_ast(
                source, function_name, start_line, end_line
            )
            if extracted:
                logger.info(
                    f"Extracted '{function_name}' via AST from {file_path}"
                )
                return extracted
        except Exception as e:
            logger.debug(f"AST extraction failed for {function_name}: {e}")

        # Strategy 2: Line-based extraction (fallback)
        logger.info(
            f"Extracting '{function_name}' via line numbers "
            f"({start_line}-{end_line}) from {file_path}"
        )
        return self._extract_by_lines(lines, start_line, end_line)

    def _extract_by_ast(
        self,
        source: str,
        function_name: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """
        Parse the file's AST and find the function definition matching
        `function_name`.

        A name alone is not always unique — the same method name commonly
        appears on more than one class in a file (`process`, `validate`,
        `__init__`, ...). When that happens we disambiguate using the
        (start_line, end_line) hint from Component 2's report rather than
        blindly taking the first AST match, which could silently return a
        different function/method than the one that was actually flagged.
        """
        tree = ast.parse(source)
        source_lines = source.splitlines(keepends=True)

        candidates = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ]

        if not candidates:
            return ""

        node = self._pick_best_candidate(candidates, start_line, end_line)

        # node.lineno points at the `def` line, not the decorator(s) above
        # it (true since Python 3.8) — start from the first decorator when
        # present so decorated functions/methods aren't truncated.
        decorator_start = (
            node.decorator_list[0].lineno if node.decorator_list else node.lineno
        )
        start = decorator_start - 1  # 0-indexed
        end = node.end_lineno        # 0-indexed end

        extracted = "".join(source_lines[start:end])
        return extracted.rstrip()

    @staticmethod
    def _pick_best_candidate(
        candidates: list,
        start_line: Optional[int],
        end_line: Optional[int],
    ):
        """
        Choose the AST node that best matches the (start_line, end_line)
        hint when several functions/methods share the same name.

        Preference order:
        1. The candidate whose line range overlaps the hint the most.
        2. If none overlap (approximate/off-by-a-few line numbers), the
           candidate whose start line is numerically closest to the hint.
        3. If no hint was given at all, the first candidate found (old
           behaviour), so callers that don't have line numbers still work.
        """
        if len(candidates) == 1 or start_line is None:
            return candidates[0]

        hint_end = end_line if end_line is not None else start_line

        def score(node) -> tuple:
            node_start = node.lineno
            node_end = node.end_lineno or node.lineno
            overlap = max(
                0, min(node_end, hint_end) - max(node_start, start_line) + 1
            )
            if overlap > 0:
                return (1, overlap)
            distance = abs(node_start - start_line)
            return (0, -distance)

        return max(candidates, key=score)

    def _extract_by_lines(
        self,
        lines: list[str],
        start_line: int,
        end_line: int,
    ) -> str:
        """
        Extract code using line numbers as fallback.
        Adjusts for 0-indexing and handles out-of-range gracefully.
        """
        # Convert to 0-indexed
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)

        extracted = "".join(lines[start:end])
        return extracted.rstrip()

    def extract_all_functions(self, file_path: str) -> dict[str, str]:
        """
        Extract ALL function definitions from a file.
        Useful for building a complete function map of the repo.

        Returns:
            Dict mapping function_name → source_code
        """
        full_path = self.repo_path / file_path

        if not full_path.exists():
            return {}

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()

        source_lines = source.splitlines(keepends=True)
        functions = {}

        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = node.lineno - 1
                    end = node.end_lineno
                    code = "".join(source_lines[start:end]).rstrip()
                    functions[node.name] = code
        except SyntaxError:
            pass

        return functions

    