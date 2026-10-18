
import os
import re
from typing import Dict, List, Optional, Set

from .models import InputConstraint, Requirement


# Supported README filenames
_README_FILENAMES = ["README.md", "Readme.md", "readme.md"]


# Recognized specification section names
_SECTION_HEADERS = {
    "args": "args",
    "arguments": "args",
    "parameters": "args",
    "returns": "returns",
    "return": "returns",
    "raises": "raises",
    "raise": "raises",
}


# Matches documented parameters such as:
# - name: description
# * `name`: description
# name (type): description
_ARG_LINE_PATTERN = re.compile(
    r"^\s*[-*]?\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*"
    r"(\([^)]*\))?\s*:\s*(.*)$"
)


# Matches documented exceptions such as:
# ValueError: invalid input
# - `TypeError`: invalid type
_RAISE_LINE_PATTERN = re.compile(
    r"^\s*[-*]?\s*`?([A-Za-z_][A-Za-z0-9_.]*)`?\s*:?\s*(.*)$"
)


# Matches Markdown headings from level 1 to level 6
_HEADER_LINE_PATTERN = re.compile(r"^(#{1,6})\s*(.+?)\s*$")


# Extracts requirements from a project's README file.
class ReadmeRequirementExtractor:

    # Main method used to extract documented requirements
    def extract(
        self,
        project_root: str,
        known_function_names: Set[str]
    ) -> List[Requirement]:

        # Locate a supported README file
        readme_path = self._find_readme(project_root)

        # No README means there are no README requirements
        if readme_path is None:
            return []

        try:

            # Read the README using UTF-8 encoding
            with open(readme_path, "r", encoding="utf-8") as file:
                content = file.read()

        # Handle file access errors without stopping analysis
        except (OSError, UnicodeError):
            return []

        # Find sections whose headings match actual function names
        function_sections = self._split_by_function_headers(
            content,
            known_function_names
        )

        # Parse each function section into a Requirement object
        requirements = []

        for function_name, lines in function_sections.items():

            requirement = self._parse_function_section(
                function_name,
                lines
            )

            # Only keep sections containing structured requirements
            if requirement is not None:
                requirements.append(requirement)

        return requirements

    # Finds a supported README filename in the project root
    @staticmethod
    def _find_readme(project_root: str) -> Optional[str]:

        for filename in _README_FILENAMES:

            # Build the full README path
            candidate = os.path.join(project_root, filename)

            # Return the first existing README file
            if os.path.isfile(candidate):
                return candidate

        return None

    # Normalizes function headings before matching
    @staticmethod
    def _normalize_header_text(text: str) -> str:

        # Remove common Markdown formatting characters
        text = text.strip().strip("*_` ")

        # Remove a trailing function signature, if present
        # Example: calculate_fee(days) becomes calculate_fee
        text = re.sub(r"\(.*\)\s*$", "", text).strip()

        return text

    # Splits README content into sections for known functions
    def _split_by_function_headers(
        self,
        content: str,
        known_function_names: Set[str]
    ) -> Dict[str, List[str]]:

        # Divide the README into individual lines
        lines = content.splitlines()

        # Stores README lines grouped by function name
        sections: Dict[str, List[str]] = {}

        # Tracks the function section currently being read
        current_function = None
        current_level = None
        buffer: List[str] = []

        for line in lines:

            # Check whether this line is a Markdown heading
            match = _HEADER_LINE_PATTERN.match(line)

            if match:

                # Determine the heading level
                level = len(match.group(1))

                # A deeper heading may be a subsection such as Args
                if (
                    current_function is not None
                    and level > current_level
                ):
                    buffer.append(line)
                    continue

                # Save the previous function section
                if current_function is not None:
                    sections[current_function] = buffer

                # Normalize the new heading text
                header_text = self._normalize_header_text(
                    match.group(2)
                )

                # Accept only headings matching actual function names
                if header_text in known_function_names:

                    current_function = header_text
                    current_level = level
                    buffer = []

                else:

                    # Ignore unrelated README sections
                    current_function = None
                    current_level = None
                    buffer = []

                continue

            # Collect lines belonging to the active function section
            if current_function is not None:
                buffer.append(line)

        # Save the final function section
        if current_function is not None:
            sections[current_function] = buffer

        return sections

    # Parses one function's README section
    def _parse_function_section(
        self,
        function_name: str,
        lines: List[str]
    ) -> Optional[Requirement]:

        # Separate Args, Returns and Raises subsections
        sub_sections = self._split_sub_sections(lines)

        # Extract documented input requirements
        inputs = self._parse_args_section(
            sub_sections.get("args")
        )

        # Extract documented output information
        expected_output = self._parse_returns_section(
            sub_sections.get("returns")
        )

        # Extract documented exceptions
        exceptions = self._parse_raises_section(
            sub_sections.get("raises")
        )

        # Do not invent requirements from an empty section
        if not inputs and not expected_output and not exceptions:
            return None

        # Preserve the existing Requirement object structure
        return Requirement(
            function_name=function_name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=exceptions,
        )

    # Separates Args, Returns and Raises sections
    @staticmethod
    def _split_sub_sections(
        lines: List[str]
    ) -> Dict[str, List[str]]:

        # Stores lines for each recognized subsection
        sections: Dict[str, List[str]] = {}

        current_key = None
        buffer: List[str] = []

        for line in lines:

            # Normalize headings such as:
            # #### Args:
            # **Args:**
            # Args:
            candidate = (
                line.strip()
                .lstrip("#")
                .strip()
                .strip("*_")
                .strip()
            )

            lowered = candidate.lower().rstrip(":")

            # Start collecting a recognized subsection
            if lowered in _SECTION_HEADERS:

                # Save the previous subsection
                if current_key:
                    sections[current_key] = buffer

                current_key = _SECTION_HEADERS[lowered]
                buffer = []
                continue

            # Collect content for the current subsection
            if current_key:
                buffer.append(line)

        # Save the final subsection
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

            # Match a parameter name and its description
            match = _ARG_LINE_PATTERN.match(line)

            if match:
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

            # Identify an exception name in each line
            match = _RAISE_LINE_PATTERN.match(line)

            if match:
                exceptions.append(match.group(1))

        return exceptions
