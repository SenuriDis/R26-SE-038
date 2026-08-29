"""
Detects specification gaps for each mapped function: whether documented
input constraints are actually enforced in code, whether documented
exceptions are actually raised, and whether a documented output is
actually returned.

Important limitation, stated up front: these are heuristic AST pattern
matches, not formal verification. "missing_input_validation" only
checks whether an `if` condition anywhere in the function references
the constrained parameter's name -- it doesn't verify the check
enforces the exact constraint (e.g. that `percentage <= 100` is
actually the comparison used, versus some unrelated check on the same
variable). Proving that would require symbolic execution, which is out
of scope for a static structural analysis component. This is worth
stating explicitly in your report as a known limitation, not something
to hide.
"""

import ast
from dataclasses import dataclass

from .code_requirement_mapper import MappingResult, MappingStatus
from .models import Requirement


@dataclass
class GapAnalysis:
    missing_input_validation: bool
    missing_exception_handling: bool
    missing_output_definition: bool
    missing_function: bool
    missing_requirement_coverage: bool


class GapDetector:
    def detect(self, mapping: MappingResult) -> GapAnalysis:
        if mapping.status == MappingStatus.DOCUMENTED_MISSING:
            # No implementation exists -- every code-level check is
            # vacuously "missing", but the requirement itself IS
            # documented, so requirement coverage isn't the problem.
            return GapAnalysis(
                missing_input_validation=True,
                missing_exception_handling=True,
                missing_output_definition=True,
                missing_function=True,
                missing_requirement_coverage=False,
            )

        if mapping.status == MappingStatus.IMPLEMENTED_UNDOCUMENTED:
            # Code exists but there's no requirement to check it against --
            # the code-level checks aren't applicable without a spec.
            return GapAnalysis(
                missing_input_validation=False,
                missing_exception_handling=False,
                missing_output_definition=False,
                missing_function=False,
                missing_requirement_coverage=True,
            )

        # DOCUMENTED_IMPLEMENTED: both exist, so compare the requirement
        # against the function's actual AST body.
        function_info = mapping.function_info
        requirement = mapping.requirement

        return GapAnalysis(
            missing_input_validation=self._missing_input_validation(function_info, requirement),
            missing_exception_handling=self._missing_exception_handling(function_info, requirement),
            missing_output_definition=self._missing_output_definition(function_info, requirement),
            missing_function=False,
            missing_requirement_coverage=False,
        )

    def _missing_input_validation(self, function_info, requirement: Requirement) -> bool:
        constrained_names = {c.name for c in requirement.inputs if c.name}
        if not constrained_names:
            return False

        referenced_names = set()
        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.If):
                for sub_node in ast.walk(node.test):
                    if isinstance(sub_node, ast.Name):
                        referenced_names.add(sub_node.id)

        return not (constrained_names & referenced_names)

    def _missing_exception_handling(self, function_info, requirement: Requirement) -> bool:
        if not requirement.exceptions:
            return False

        expected = set(requirement.exceptions)
        raised = set()
        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.Raise) and node.exc is not None:
                name = self._get_exception_name(node.exc)
                if name:
                    raised.add(name)

        return not (expected & raised)

    def _missing_output_definition(self, function_info, requirement: Requirement) -> bool:
        if not requirement.expected_output:
            return False

        for node in ast.walk(function_info.ast_node):
            if isinstance(node, ast.Return) and node.value is not None:
                return False

        return True

    @staticmethod
    def _get_exception_name(exc_node):
        if isinstance(exc_node, ast.Call):
            exc_node = exc_node.func
        if isinstance(exc_node, ast.Name):
            return exc_node.id
        if isinstance(exc_node, ast.Attribute):
            return exc_node.attr
        return None
