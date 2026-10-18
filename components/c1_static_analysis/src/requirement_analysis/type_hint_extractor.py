
import ast
from typing import List

from .models import InputConstraint, Requirement


class TypeHintRequirementExtractor:
    """Extract input and output requirements from Python type annotations."""

    def extract(self, tree: ast.AST) -> List[Requirement]:
        requirements = []

        # Handle an invalid or missing AST safely.
        if not isinstance(tree, ast.AST):
            return requirements

        for node in ast.walk(tree):
            # Support regular and asynchronous functions.
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            inputs = []

            # Collect positional-only, positional, and keyword-only arguments.
            arguments = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )

            # Include *args and **kwargs when annotated.
            if node.args.vararg:
                arguments.append(node.args.vararg)

            if node.args.kwarg:
                arguments.append(node.args.kwarg)

            # Extract parameter annotations.
            for argument in arguments:
                if argument.annotation is not None:
                    annotation = self._annotation_to_str(argument.annotation)

                    if annotation:
                        inputs.append(
                            InputConstraint(
                                name=argument.arg,
                                constraint=annotation,
                            )
                        )

            # Extract the expected return type.
            expected_output = ""
            if node.returns is not None:
                expected_output = self._annotation_to_str(node.returns)

            # Ignore functions without any type annotations.
            if inputs or expected_output:
                requirements.append(
                    Requirement(
                        function_name=node.name,
                        inputs=inputs,
                        expected_output=expected_output,
                        exceptions=[],
                    )
                )

        return requirements

    @staticmethod
    def _annotation_to_str(annotation: ast.AST) -> str:
        """Convert an annotation AST node into readable text."""
        try:
            return ast.unparse(annotation)
        except (AttributeError, TypeError, ValueError):
            return ""
