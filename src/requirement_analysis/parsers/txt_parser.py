"""
Parses requirement documents supplied as plain TXT.

Format: one block per function, blocks separated by a line of '---'.
Each block uses simple 'key: value' lines. Multiple 'input' lines are
allowed per block, one constraint each.

Example:
    function: calculate_fee
    input: days >= 0
    output: fee amount
    exception: ValueError
    ---
    function: enrol_student
    input: capacity > 0
    output: enrollment confirmation
"""

from typing import List

from .base_parser import RequirementParser
from ..models import InputConstraint, Requirement


class TxtRequirementParser(RequirementParser):
    BLOCK_SEPARATOR = "---"

    def parse(self, file_path: str) -> List[Requirement]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            self._fail(file_path, str(e))

        blocks = [b.strip() for b in content.split(self.BLOCK_SEPARATOR) if b.strip()]
        if not blocks:
            self._fail(file_path, "no requirement blocks found")

        return [self._parse_block(block, file_path, i) for i, block in enumerate(blocks)]

    def _parse_block(self, block: str, file_path: str, index: int) -> Requirement:
        function_name = ""
        inputs: List[InputConstraint] = []
        expected_output = ""
        exceptions: List[str] = []

        for line in block.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "function":
                function_name = value
            elif key == "input":
                inputs.append(self._parse_input_line(value))
            elif key == "output":
                expected_output = value
            elif key == "exception":
                exceptions.append(value)

        if not function_name:
            self._fail(file_path, f"block {index} missing 'function:' line")

        return Requirement(
            function_name=function_name,
            inputs=inputs,
            expected_output=expected_output,
            exceptions=exceptions,
        )

    @staticmethod
    def _parse_input_line(value: str) -> InputConstraint:
        # e.g. "days >= 0" -> name="days", constraint=">= 0"
        parts = value.split(None, 1)
        if len(parts) == 2:
            return InputConstraint(name=parts[0], constraint=parts[1])
        return InputConstraint(name=value, constraint="")
