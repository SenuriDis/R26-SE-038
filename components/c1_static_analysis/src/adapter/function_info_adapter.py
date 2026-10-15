"""
Bridges the existing AST analysis modules into a stable FunctionInfo
contract that the requirement-analysis layer depends on.

Why this exists: analyze_file() in main.py already produces
function_complexities and dependencies as flat, JSON-friendly dicts
keyed by function name -- perfect for the frontend and MongoDB, but
they don't retain the actual ast.FunctionDef node. The gap detector
(Phase 3) needs the real node so it can inspect a function's body
(e.g. "is there an `if` guarding this parameter", "is there a
matching `raise`").

This adapter does NOT change or duplicate the logic in src/metrics or
src/extractor. It reuses NestingDepthCalculator exactly as-is -- that
class already accepts any AST node, not just a full tree, so calling
it per-function requires zero changes to existing code.
"""

import ast
from dataclasses import dataclass, field
from typing import Dict, List

from src.metrics.nesting_depth_calculator import NestingDepthCalculator


@dataclass
class FunctionInfo:
    """Stable, requirement-analysis-facing view of one function."""
    name: str
    ast_node: ast.FunctionDef
    cyclomatic_complexity: int
    nesting_depth: int
    lines_of_code: int
    dependencies: List[str] = field(default_factory=list)

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)


class FunctionInfoAdapter:
    def build(
        self,
        tree: ast.AST,
        function_complexities: Dict[str, int],
        dependencies: Dict[str, List[str]],
    ) -> List[FunctionInfo]:
        """
        tree: the AST returned by parse_python_file()
        function_complexities: output of FunctionComplexityCalculator().extract(tree)
        dependencies: output of DependencyExtractor().extract(tree)
        """
        function_infos = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            name = node.name

            # Reuse the existing calculator, scoped to just this function's node.
            nesting_depth = NestingDepthCalculator().calculate(node)

            function_infos.append(
                FunctionInfo(
                    name=name,
                    ast_node=node,
                    cyclomatic_complexity=function_complexities.get(name, 1),
                    nesting_depth=nesting_depth,
                    lines_of_code=self._count_lines(node),
                    dependencies=dependencies.get(name, []),
                )
            )

        return function_infos

    @staticmethod
    def _count_lines(node: ast.FunctionDef) -> int:
        end_line = getattr(node, "end_lineno", None)
        if end_line is None:
            return 0
        return end_line - node.lineno + 1
