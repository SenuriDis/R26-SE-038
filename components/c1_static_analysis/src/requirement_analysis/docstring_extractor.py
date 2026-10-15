"""
Auto-extracts Requirement objects directly from a function's own
docstring, instead of requiring a separate hand-written TXT/JSON
requirement file.

Why this exists: real, third-party repositories don't ship
requirements in your custom format -- they document behavior through
docstrings. This extractor treats a well-formed docstring as the
specification itself, so the system can run against any real codebase
without anyone manually authoring a requirement document per function.

Supported convention: Google-style docstrings, e.g.

    def calculate_fee(days):
        \"\"\"
        Calculate a late fee.

        Args:
            days (int): number of days overdue, must be >= 0.

        Returns:
            float: the fee amount.

        Raises:
            ValueError: if days is negative.
        \"\"\"

Limitations (state these explicitly in your report, don't hide them):
  - Only Google-style Args/Returns/Raises sections are recognised.
    NumPy-style and reST-style docstrings are not handled -- flagged
    here as a known scope boundary, not a silent failure.
  - Input "constraints" are captured as free text describing the
    parameter, not parsed into a formal comparison like ">=0". This is
    consistent with gap_detector.py, which only checks whether a
    parameter is documented at all (does the code reference that
    parameter name in a conditional), not whether an exact numeric
    constraint is enforced.
  - A function with no docstring, or a docstring that doesn't contain
    any of the three recognised sections, produces no Requirement --
    this is correct behavior, not a bug. Undocumented code should fall
    into the existing "implemented_undocumented" bucket, not have a
    requirement invented for it.
"""

import ast
import re
from typing import Dict, List, Optional

from .models import InputConstraint, Requirement

_SECTION_HEADERS = {
    "args": "args",
    "arguments": "args",
    "parameters": "args",
    "returns": "returns",
    "return": "returns",
    "raises": "raises",
    "raise": "raises",
}

_ARG_LINE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?\s*:\s*(.*)$")
_RAISE_LINE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*:?\s*(.*)$")


class DocstringRequirementExtractor:
    def extract(self, tree: ast.AST) -> List[Requirement]:
        requirements = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            docstring = ast.get_docstring(node)
            if not docstring:
                continue

            requirement = self._parse_docstring(node.name, docstring)
            if requirement is not None:
                requirements.append(requirement)

        return requirements

    def _parse_docstring(self, function_name: str, docstring: str) -> Optional[Requirement]:
        sections = self._split_sections(docstring)

        inputs = self._parse_args_section(sections.get("args"))
        expected_output = self._parse_returns_section(sections.get("returns"))
        exceptions = self._parse_raises_section(sections.get("raises"))

        # Nothing structured found -- same as having no docstring at all.
        if not inputs and not expected_output and not exceptions:
            return None

        return Requirement(
            function_name=function_name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=exceptions,
        )

    @staticmethod
    def _split_sections(docstring: str) -> Dict[str, List[str]]:
        lines = docstring.splitlines()
        sections: Dict[str, List[str]] = {}
        current_key = None
        buffer: List[str] = []

        for line in lines:
            lowered = line.strip().lower().rstrip(":")

            if lowered in _SECTION_HEADERS:
                if current_key:
                    sections[current_key] = buffer
                current_key = _SECTION_HEADERS[lowered]
                buffer = []
                continue

            if current_key:
                buffer.append(line)

        if current_key:
            sections[current_key] = buffer

        return sections

    @staticmethod
    def _parse_args_section(lines: Optional[List[str]]) -> List[InputConstraint]:
        if not lines:
            return []

        inputs = []
        for line in lines:
            match = _ARG_LINE_PATTERN.match(line)
            if match:
                name = match.group(1)
                description = match.group(3).strip()
                inputs.append(InputConstraint(name=name, constraint=description))

        return inputs

    @staticmethod
    def _parse_returns_section(lines: Optional[List[str]]) -> str:
        if not lines:
            return ""
        return " ".join(line.strip() for line in lines if line.strip())

    @staticmethod
    def _parse_raises_section(lines: Optional[List[str]]) -> List[str]:
        if not lines:
            return []

        exceptions = []
        for line in lines:
            match = _RAISE_LINE_PATTERN.match(line)
            if match:
                exceptions.append(match.group(1))

        return exceptions
