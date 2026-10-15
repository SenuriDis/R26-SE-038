"""
Data models for requirement-aware static analysis.

These are the structured representations produced by parsing requirement
documents (TXT or JSON), before being mapped against AST-discovered code
in later phases.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class InputConstraint:
    """A single constraint on one input parameter, e.g. days >= 0."""
    name: str
    constraint: str


@dataclass
class Requirement:
    """A structured requirement extracted for a single function."""
    function_name: str
    inputs: List[InputConstraint] = field(default_factory=list)
    expected_output: str = ""
    exceptions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "function_name": self.function_name,
            "inputs": [
                {"name": c.name, "constraint": c.constraint}
                for c in self.inputs
            ],
            "expected_output": self.expected_output,
            "exceptions": list(self.exceptions),
        }
