"""
Auto-extracts Requirement objects from a project's README, using the
same Args/Returns/Raises convention as docstrings, scoped strictly to
functions that actually exist in the analyzed codebase.

Why this exists: some projects document individual functions in their
README instead of (or in addition to) docstrings -- typically as a
hand-maintained API reference section.

Why it's scoped so narrowly: empirically, most READMEs are project-level
prose (installation instructions, badges, a description) and don't
document individual functions at all -- verified directly against both
programiz/Calculator (no function-level content whatsoever) and
python-humanize/humanize (points to ReadTheDocs instead of documenting
functions inline). Given that reality, this extractor requires TWO
signals before creating a Requirement for a function:
  1. A markdown header whose text exactly matches a real function name
     found in the analyzed code
  2. A recognized Args/Parameters/Returns/Raises sub-structure nested
     beneath that header

A README section that merely mentions a function in prose, with nothing
structured beneath it, produces nothing here -- consistent with how an
under-specified docstring also produces nothing. This avoids inventing
a "perfect coverage" requirement from a heading with no actual content
to check the code against.

Unlike DocstringRequirementExtractor and TypeHintRequirementExtractor
(which operate on one file's AST), this operates on a PROJECT ROOT,
since a README describes the whole repository, not one file.
"""

import os
import re
from typing import Dict, List, Optional, Set

from .models import InputConstraint, Requirement

_README_FILENAMES = ["README.md", "Readme.md", "readme.md"]

_SECTION_HEADERS = {
    "args": "args",
    "arguments": "args",
    "parameters": "args",
    "returns": "returns",
    "return": "returns",
    "raises": "raises",
    "raise": "raises",
}

# "- name: description", "* `name`: description", "name (type): description"
_ARG_LINE_PATTERN = re.compile(
    r"^\s*[-*]?\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*(\([^)]*\))?\s*:\s*(.*)$"
)
_RAISE_LINE_PATTERN = re.compile(r"^\s*[-*]?\s*`?([A-Za-z_][A-Za-z0-9_.]*)`?\s*:?\s*(.*)$")

# Any markdown header line: "#", "## name", "### `name(args)`"
_HEADER_LINE_PATTERN = re.compile(r"^(#{1,6})\s*(.+?)\s*$")


class ReadmeRequirementExtractor:
    def extract(self, project_root: str, known_function_names: Set[str]) -> List[Requirement]:
        readme_path = self._find_readme(project_root)
        if readme_path is None:
            return []

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return []

        function_sections = self._split_by_function_headers(content, known_function_names)

        requirements = []
        for function_name, lines in function_sections.items():
            requirement = self._parse_function_section(function_name, lines)
            if requirement is not None:
                requirements.append(requirement)

        return requirements

    @staticmethod
    def _find_readme(project_root: str) -> Optional[str]:
        for filename in _README_FILENAMES:
            candidate = os.path.join(project_root, filename)
            if os.path.isfile(candidate):
                return candidate
        return None

    @staticmethod
    def _normalize_header_text(text: str) -> str:
        # "`calculate_fee(days)`" and "calculate_fee" both normalize to
        # "calculate_fee", so headers written either way are matched.
        text = text.strip().strip("*_` ")
        text = re.sub(r"\(.*\)\s*$", "", text).strip()
        return text

    def _split_by_function_headers(
        self, content: str, known_function_names: Set[str]
    ) -> Dict[str, List[str]]:
        lines = content.splitlines()
        sections: Dict[str, List[str]] = {}
        current_function = None
        current_level = None
        buffer: List[str] = []

        for line in lines:
            match = _HEADER_LINE_PATTERN.match(line)

            if match:
                level = len(match.group(1))

                # A DEEPER header while inside a function's section (e.g.
                # "#### Args" under "### calculate_fee") is a sub-section,
                # not a new top-level boundary -- keep buffering it.
                if current_function is not None and level > current_level:
                    buffer.append(line)
                    continue

                if current_function is not None:
                    sections[current_function] = buffer

                header_text = self._normalize_header_text(match.group(2))
                if header_text in known_function_names:
                    current_function = header_text
                    current_level = level
                    buffer = []
                else:
                    current_function = None
                    current_level = None
                    buffer = []
                continue

            if current_function is not None:
                buffer.append(line)

        if current_function is not None:
            sections[current_function] = buffer

        return sections

    def _parse_function_section(self, function_name: str, lines: List[str]) -> Optional[Requirement]:
        sub_sections = self._split_sub_sections(lines)

        inputs = self._parse_args_section(sub_sections.get("args"))
        expected_output = self._parse_returns_section(sub_sections.get("returns"))
        exceptions = self._parse_raises_section(sub_sections.get("raises"))

        if not inputs and not expected_output and not exceptions:
            return None

        return Requirement(
            function_name=function_name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=exceptions,
        )

    @staticmethod
    def _split_sub_sections(lines: List[str]) -> Dict[str, List[str]]:
        sections: Dict[str, List[str]] = {}
        current_key = None
        buffer: List[str] = []

        for line in lines:
            # Sub-headers may appear as "#### Args:", "**Args:**", or
            # plain "Args:" -- normalize all three before matching.
            candidate = line.strip().lstrip("#").strip().strip("*_").strip()
            lowered = candidate.lower().rstrip(":")

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
                inputs.append(
                    InputConstraint(name=match.group(1), constraint=match.group(3).strip())
                )
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
