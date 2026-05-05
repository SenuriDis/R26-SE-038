import ast
import re
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ASTValidationResult:
    is_valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_line: Optional[int] = None


@dataclass
class DryRunResult:
    is_valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    tests_collected: int = 0


def ast_parse_check(code: str) -> ASTValidationResult:
    """
    Check if the given Python code is syntactically valid.
    Returns details about any error found so Agent 2 knows what to fix.
    """
    try:
        ast.parse(code)
        return ASTValidationResult(is_valid=True)
    except SyntaxError as e:
        return ASTValidationResult(
            is_valid=False,
            error_type=type(e).__name__,
            error_message=str(e),
            error_line=e.lineno,
        )
    except Exception as e:
        return ASTValidationResult(
            is_valid=False,
            error_type=type(e).__name__,
            error_message=str(e),
        )


def pytest_dry_run(test_code: str, timeout: int = 15) -> DryRunResult:
    """
    Write the test code to a temporary file and run pytest --collect-only.
    This catches import errors and undefined names without actually running tests.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="agent2_dryrun_",
        delete=False,
    ) as tmp:
        tmp.write(test_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout + result.stderr

        if result.returncode == 0:
            match = re.search(r"(\d+)\s+test[s]?\s+collected", output)
            collected = int(match.group(1)) if match else 0
            return DryRunResult(is_valid=True, tests_collected=collected)
        else:
            error_msg = _extract_error(output)
            return DryRunResult(
                is_valid=False,
                error_type="CollectionError",
                error_message=error_msg,
            )

    except subprocess.TimeoutExpired:
        return DryRunResult(
            is_valid=False,
            error_type="Timeout",
            error_message=f"pytest timed out after {timeout}s",
        )
    except Exception as e:
        return DryRunResult(
            is_valid=False,
            error_type=type(e).__name__,
            error_message=str(e),
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def extract_test_functions(code: str) -> list[str]:
    """
    Return the names of all test functions in the given code.
    Used to verify Agent 1 actually generated callable tests.
    """
    try:
        tree = ast.parse(code)
        return [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith("test_")
        ]
    except SyntaxError:
        return []


def extract_imports(code: str) -> list[str]:
    """
    Extract all import statements from the code.
    Used by Agent 2 to check for hallucinated imports.
    """
    try:
        tree = ast.parse(code)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                names = ", ".join(a.name for a in node.names)
                imports.append(f"from {node.module} import {names}")
        return imports
    except SyntaxError:
        return []


def strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences that LLMs sometimes wrap their output in.
    e.g. ```python ... ``` becomes just the code inside.
    """
    text = text.strip()
    text = re.sub(r"^```(?:python)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_error(output: str) -> str:
    """Pull the most useful error lines from pytest output."""
    lines = output.strip().splitlines()
    error_lines = [l for l in lines if "ERROR" in l or "Error" in l]
    if error_lines:
        return "\n".join(error_lines[:5])
    return "\n".join(lines[-5:]) if lines else "Unknown error"