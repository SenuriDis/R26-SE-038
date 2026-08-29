"""
Auto-extracts Requirement objects from a function's type hints, as a
second automated source alongside DocstringRequirementExtractor.

Why this exists: plenty of real repositories have parameter/return type
annotations without full Google-style docstrings. A type hint IS real
information the original developer wrote about the function's
contract -- it's fair game as a (weaker) specification source, and it
means the system isn't entirely dependent on docstring conventions.

Design note: this deliberately only fires for functions that have AT
LEAST ONE annotation. A function with zero annotations and zero
docstring gets nothing from either extractor -- which is correct: if
the original developer documented nothing at all, there is genuinely
no specification to compare against, and the system should say so via
implemented_undocumented, not invent one.

The "constraint" captured here is just the type name itself (e.g.
"int", "str") -- much weaker than a Google-style docstring's prose
description, but still a real, extractable signal. If a function has
BOTH a parsed docstring requirement AND type hints, prefer the
docstring version (richer) -- see composite_extractor.py.
"""

import ast
from typing import List, Optional

from .models import InputConstraint, Requirement


class TypeHintRequirementExtractor:
    def extract(self, tree: ast.AST) -> List[Requirement]:
        requirements = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            requirement = self._from_annotations(node)
            if requirement is not None:
                requirements.append(requirement)

        return requirements

    def _from_annotations(self, node: ast.FunctionDef) -> Optional[Requirement]:
        inputs = []
        for arg in node.args.args:
            if arg.annotation is not None:
                inputs.append(
                    InputConstraint(name=arg.arg, constraint=self._annotation_to_str(arg.annotation))
                )

        expected_output = ""
        if node.returns is not None:
            expected_output = self._annotation_to_str(node.returns)

        if not inputs and not expected_output:
            return None

        return Requirement(
            function_name=node.name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=[],  # type hints don't declare exceptions (no exception count = check not applicable)
        )

    @staticmethod
    def _annotation_to_str(annotation: ast.AST) -> str:
        try:
            return ast.unparse(annotation)
        except Exception:
            return ""
