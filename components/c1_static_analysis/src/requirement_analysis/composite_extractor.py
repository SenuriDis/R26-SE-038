"""
Combines DocstringRequirementExtractor, ReadmeRequirementExtractor, and
TypeHintRequirementExtractor into a single automated requirement
source, so the system gets the richest available specification for
each function without any manual authoring.

Priority per function (richest wins when multiple sources agree on the
same function name):
  1. A parsed Google-style docstring requirement -- richest source,
     lives right next to the code, most likely to be kept in sync.
  2. A parsed README API-reference requirement -- structurally as rich
     as a docstring (can express exceptions), but less commonly present
     and more prone to drifting out of sync with the actual code.
  3. A type-hint-derived requirement -- weakest, but broadly available.
  4. Nothing -- the function is genuinely undocumented by every
     measure, and correctly falls into implemented_undocumented.
"""

import ast
from typing import Dict, List, Optional

from .models import Requirement
from .docstring_extractor import DocstringRequirementExtractor
from .type_hint_extractor import TypeHintRequirementExtractor


class CompositeRequirementExtractor:
    def __init__(self):
        self._docstring_extractor = DocstringRequirementExtractor()
        self._type_hint_extractor = TypeHintRequirementExtractor()

    def extract(
        self,
        tree: ast.AST,
        readme_requirements: Optional[Dict[str, Requirement]] = None,
    ) -> List[Requirement]:
        docstring_requirements = {
            r.function_name: r for r in self._docstring_extractor.extract(tree)
        }
        type_hint_requirements = {
            r.function_name: r for r in self._type_hint_extractor.extract(tree)
        }
        readme_requirements = readme_requirements or {}

        merged = dict(type_hint_requirements)
        merged.update(readme_requirements)     # README beats type hints
        merged.update(docstring_requirements)  # docstring beats everything

        return list(merged.values())
