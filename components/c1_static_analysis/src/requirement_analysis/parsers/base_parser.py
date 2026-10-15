"""
Abstract base for requirement document parsers.

Each concrete parser (TXT, JSON, ...) implements `parse()` and returns a
list of Requirement objects. New formats can be added later by adding a
new subclass and registering it in parser_factory.py -- nothing that
already works needs to change.
"""

from abc import ABC, abstractmethod
from typing import List

from ..models import Requirement


class RequirementParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Requirement]:
        """Parse a requirement document into a list of Requirement objects."""
        raise NotImplementedError

    @staticmethod
    def _fail(file_path: str, reason: str) -> None:
        raise ValueError(f"Failed to parse requirement file '{file_path}': {reason}")
