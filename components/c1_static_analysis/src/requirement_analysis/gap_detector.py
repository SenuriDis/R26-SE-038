
"""
Detect specification gaps for mapped functions.

Checks whether:
1. Documented input constraints are referenced in conditional checks.
2. Documented exceptions are raised in the implementation.
3. A documented output has a corresponding return statement.
4. A documented function is implemented.
5. An implemented function has documented requirements.

IMPORTANT:
These are heuristic AST checks, not formal verification.
They identify structural patterns but cannot prove that a constraint
is enforced correctly in every possible execution path.
"""

import ast
from dataclasses import dataclass

from .code_requirement_mapper import MappingResult, MappingStatus
from .models import Requirement


@dataclass
class GapAnalysis:
    """Stores the specification gaps identified for a function."""

    missing_input_validation: bool
    missing_exception_handling: bool
    missing_output_definition: bool
    missing_function: bool
    missing_requirement_coverage: bool


class GapDetector:
    """Detects possible gaps between requirements and implementation."""

    def detect(self, mapping: MappingResult) -> GapAnalysis:
        """Analyze a function according to its mapping status."""

        # Case 1: A requirement exists, but the function is not implemented.
        # All code-level checks are marked as missing because there is no
        # function body to inspect. Requirement coverage itself exists.
        if mapping.status == MappingStatus.DOCUMENTED_MISSING:
            return GapAnalysis(
                missing_input_validation=True,
                missing_exception_handling=True,
                missing_output_definition=True,
                missing_function=True,
                missing_requirement_coverage=False,
            )

        # Case 2: The function exists, but it has no documented requirement.
        # Code-level gaps cannot be assessed against a missing specification.
        if mapping.status == MappingStatus.IMPLEMENTED_UNDOCUMENTED:
            return GapAnalysis(
                missing_input_validation=False,
                missing_exception_handling=False,
                missing_output_definition=False,
                missing_function=False,
                missing_requirement_coverage=True,
            )

        # Case 3: Both the implementation and its requirement exist.
        # Compare the function's AST with the documented requirement.
        function_info = mapping.function_info
        requirement = mapping.requirement

        return GapAnalysis(
            missing_input_validation=self._missing_input_validation(
                function_info, requirement
            ),
            missing_exception_handling=self._missing_exception_handling(
                function_info, requirement
            ),
            missing_output_definition=self._missing_output_definition(
                function_info, requirement
            ),
            missing_function=False,
            missing_requirement_coverage=False,
        )

    def _missing_input_validation(
        self, function_info, requirement: Requirement
    ) -> bool:
        """Check whether every constrained input appears in an if condition."""

        # Collect the names of documented inputs that have constraints.
        constrained_names = {
            constraint.name
            for constraint in requirement.inputs
            if constraint.name
        }

        # If no constrained inputs are documented, there is nothing to check.
        if not constrained_names:
            return False

        # Store variable names referenced inside if conditions.
        condition_names = set()

        # Walk through the function AST to find conditional statements.
        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.If):

                # Inspect the condition of the if statement.
                for child in ast.walk(node.test):
                    if isinstance(child, ast.Name):
                        condition_names.add(child.id)

        # Every constrained input must appear in at least one condition.
        # For example, checking 'price' does not count as checking
        # 'percentage' when both parameters have documented constraints.
        #
        # Limitation: this checks parameter names only. It does not prove
        # that the condition enforces the exact documented constraint.
        return not constrained_names.issubset(condition_names)

    def _missing_exception_handling(
        self, function_info, requirement: Requirement
    ) -> bool:
        """Check whether a documented exception is raised in the function."""

        # If no exceptions are documented, exception handling is not required
        # by this requirement.
        if not requirement.exceptions:
            return False

        # Store the exception names required by the specification.
        expected = set(requirement.exceptions)

        # Store exception names found in raise statements in the AST.
        raised = set()

        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.Raise) and node.exc is not None:

                # Extract the exception class name from the raise expression.
                name = self._get_exception_name(node.exc)

                if name:
                    raised.add(name)

        # A gap exists if none of the documented exceptions is raised.
        return not bool(expected & raised)

    def _missing_output_definition(
        self, function_info, requirement: Requirement
    ) -> bool:
        """Check whether a documented output has a non-empty return."""

        # An output check is not applicable when no output is documented.
        if not requirement.expected_output:
            return False

        # Look for a return statement that returns a value.
        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.Return) and node.value is not None:
                return False

        # No non-empty return statement was found.
        return True

    @staticmethod
    def _get_exception_name(exc_node):
        """Extract an exception name from an AST raise expression."""

        # Handle expressions such as ValueError("Invalid input").
        if isinstance(exc_node, ast.Call):
            exc_node = exc_node.func

        # Handle a direct exception name such as ValueError.
        if isinstance(exc_node, ast.Name):
            return exc_node.id

        # Handle qualified exception names such as errors.ValueError.
        if isinstance(exc_node, ast.Attribute):
            return exc_node.attr

        # Return None if the exception name cannot be determined.
        return None
