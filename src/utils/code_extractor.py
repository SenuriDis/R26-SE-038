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
            extracted = self._extract_by_ast(source, function_name)
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

    def _extract_by_ast(self, source: str, function_name: str) -> str:
        """
        Parse the file's AST and find the exact function definition.
        This is more reliable than line numbers because it handles
        decorators, nested functions, and methods correctly.
        """
        tree = ast.parse(source)
        source_lines = source.splitlines(keepends=True)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    # Get the start line including decorators
                    start = node.lineno - 1  # 0-indexed
                    end = node.end_lineno    # 0-indexed end

                    extracted = "".join(source_lines[start:end])
                    return extracted.rstrip()

        return ""

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