
import ast
import re
from typing import Dict, List, Optional

from .models import InputConstraint, Requirement


# Maps recognized docstring section names to standard names
_SECTION_HEADERS = {
    "args": "args",
    "arguments": "args",
    "parameters": "args",
    "returns": "returns",
    "return": "returns",
    "raises": "raises",
    "raise": "raises",
}


# Matches parameter documentation such as:
# days (int): number of days overdue
# days: number of days overdue
_ARG_LINE_PATTERN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?\s*:\s*(.*)$"
)


# Matches documented exception names such as:
# ValueError: invalid input
_RAISE_LINE_PATTERN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*:?\s*(.*)$"
)


# Extracts requirements from function docstrings.
class DocstringRequirementExtractor:

    # Extract requirements from all documented functions in the AST
    def extract(self, tree: ast.AST) -> List[Requirement]:

        # Stores extracted requirements
        requirements = []

        # Traverse all AST nodes
        for node in ast.walk(tree):

            # Process regular and asynchronous functions
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue

            # Read the function's docstring
            docstring = ast.get_docstring(node)

            # Skip functions without docstrings
            if not docstring:
                continue

            # Parse the structured documentation
            requirement = self._parse_docstring(
                node.name,
                docstring
            )

            # Add only valid, structured requirements
            if requirement is not None:
                requirements.append(requirement)

        return requirements

    # Parses a single function's docstring
    def _parse_docstring(
        self,
        function_name: str,
        docstring: str
    ) -> Optional[Requirement]:

        # Separate the Args, Returns and Raises sections
        sections = self._split_sections(docstring)

        # Extract input requirements
        inputs = self._parse_args_section(
            sections.get("args")
        )

        # Extract expected output
        expected_output = self._parse_returns_section(
            sections.get("returns")
        )

        # Extract documented exceptions
        exceptions = self._parse_raises_section(
            sections.get("raises")
        )

        # Do not invent requirements from unstructured documentation
        if not inputs and not expected_output and not exceptions:
            return None

        # Preserve the existing Requirement structure
        return Requirement(
            function_name=function_name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=exceptions,
        )

    # Separates a docstring into recognized sections
    @staticmethod
    def _split_sections(
        docstring: str
    ) -> Dict[str, List[str]]:

        # Divide the docstring into lines
        lines = docstring.splitlines()

        # Stores the content of each section
        sections: Dict[str, List[str]] = {}

        current_key = None
        buffer: List[str] = []

        for line in lines:

            # Normalize section headers such as Args: and Returns:
            lowered = line.strip().lower().rstrip(":")

            # Check whether the line starts a recognized section
            if lowered in _SECTION_HEADERS:

                # Save the previous section
                if current_key:
                    sections[current_key] = buffer

                current_key = _SECTION_HEADERS[lowered]
                buffer = []
                continue

            # Collect lines belonging to the current section
            if current_key:
                buffer.append(line)

        # Save the final section
        if current_key:
            sections[current_key] = buffer

        return sections

    # Extracts documented function parameters
    @staticmethod
    def _parse_args_section(
        lines: Optional[List[str]]
    ) -> List[InputConstraint]:

        if not lines:
            return []

        inputs = []

        for line in lines:

            # Match a parameter name and optional type annotation
            match = _ARG_LINE_PATTERN.match(line)

            if match:

                # Store the parameter description as its constraint
                inputs.append(
                    InputConstraint(
                        name=match.group(1),
                        constraint=match.group(3).strip()
                    )
                )

        return inputs

    # Extracts the expected output description
    @staticmethod
    def _parse_returns_section(
        lines: Optional[List[str]]
    ) -> str:

        if not lines:
            return ""

        # Combine non-empty lines into one description
        return " ".join(
            line.strip()
            for line in lines
            if line.strip()
        )

    # Extracts documented exception names
    @staticmethod
    def _parse_raises_section(
        lines: Optional[List[str]]
    ) -> List[str]:

        if not lines:
            return []

        exceptions = []

        for line in lines:

            # Match the documented exception name
            match = _RAISE_LINE_PATTERN.match(line)

            if match:
                exceptions.append(match.group(1))

        return exceptions
