"""
Selects the correct RequirementParser implementation based on file extension.

Adding a new format later (e.g. YAML) means adding one parser class and
registering it below -- nothing else in the pipeline changes.
"""

import os

from .base_parser import RequirementParser
from .json_parser import JsonRequirementParser
from .txt_parser import TxtRequirementParser


class RequirementParserFactory:
    _PARSERS_BY_EXTENSION = {
        ".json": JsonRequirementParser,
        ".txt": TxtRequirementParser,
    }

    @classmethod
    def get_parser(cls, file_path: str) -> RequirementParser:
        _, ext = os.path.splitext(file_path)
        parser_cls = cls._PARSERS_BY_EXTENSION.get(ext.lower())
        if parser_cls is None:
            supported = ", ".join(cls._PARSERS_BY_EXTENSION)
            raise ValueError(
                f"Unsupported requirement file type '{ext}'. Supported: {supported}"
            )
        return parser_cls()
