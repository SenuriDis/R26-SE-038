
import ast
from dataclasses import dataclass, field
from typing import Dict, List

from src.metrics.nesting_depth_calculator import NestingDepthCalculator


# Stores the analysis information required for each function.
# This provides a consistent interface for requirement analysis.
@dataclass
class FunctionInfo:

    # Function name
    name: str

    # AST node containing the function's source structure
    ast_node: ast.AST

    # Calculated cyclomatic complexity
    cyclomatic_complexity: int

    # Maximum nesting depth within the function
    nesting_depth: int

    # Number of source lines occupied by the function
    lines_of_code: int

    # Functions called by this function
    dependencies: List[str] = field(default_factory=list)

    # Returns the number of recorded dependencies
    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)


# Converts AST analysis results into FunctionInfo objects.
class FunctionInfoAdapter:

    def build(
        self,
        tree: ast.AST,
        function_complexities: Dict[str, int],
        dependencies: Dict[str, List[str]],
    ) -> List[FunctionInfo]:

        # Stores information for all discovered functions
        function_infos = []

        # Traverse the AST to find function definitions
        for node in ast.walk(tree):

            # Support regular and asynchronous functions
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue

            # Get the function name
            name = node.name

            # Calculate nesting depth for this function's AST node
            nesting_depth = NestingDepthCalculator().calculate(node)

            # Build a FunctionInfo object using existing analysis results
            function_infos.append(
                FunctionInfo(
                    name=name,
                    ast_node=node,
                    cyclomatic_complexity=function_complexities.get(
                        name, 1
                    ),
                    nesting_depth=nesting_depth,
                    lines_of_code=self._count_lines(node),
                    dependencies=dependencies.get(name, []),
                )
            )

        # Return the list of function information objects
        return function_infos

    # Counts the source lines occupied by a function
    @staticmethod
    def _count_lines(node: ast.AST) -> int:

        # Get the last line of the function, if available
        end_line = getattr(node, "end_lineno", None)

        # Return zero if line information is unavailable
        if end_line is None:
            return 0

        # Calculate the inclusive line count
        return end_line - node.lineno + 1
