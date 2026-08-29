"""
Compares AST-discovered functions (via FunctionInfoAdapter) against
parsed Requirement objects, classifying each function name into one of
three states.

function_info is left loosely typed (not importing FunctionInfo
directly) so this module doesn't force a hard dependency on
src.adapter -- it only needs an object with a `.name` attribute,
which keeps the two packages independently testable.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .models import Requirement


class MappingStatus(Enum):
    DOCUMENTED_IMPLEMENTED = "documented_implemented"
    DOCUMENTED_MISSING = "documented_missing"
    IMPLEMENTED_UNDOCUMENTED = "implemented_undocumented"


@dataclass
class MappingResult:
    function_name: str
    status: MappingStatus
    function_info: Optional[object]   # a FunctionInfo, or None
    requirement: Optional[Requirement]


class CodeRequirementMapper:
    def map(self, function_infos: List, requirements: List[Requirement]) -> List[MappingResult]:
        functions_by_name = {fi.name: fi for fi in function_infos}
        requirements_by_name = {r.function_name: r for r in requirements}

        all_names = set(functions_by_name) | set(requirements_by_name)

        results = []
        for name in sorted(all_names):
            function_info = functions_by_name.get(name)
            requirement = requirements_by_name.get(name)

            if function_info and requirement:
                status = MappingStatus.DOCUMENTED_IMPLEMENTED
            elif requirement and not function_info:
                status = MappingStatus.DOCUMENTED_MISSING
            else:
                status = MappingStatus.IMPLEMENTED_UNDOCUMENTED

            results.append(
                MappingResult(
                    function_name=name,
                    status=status,
                    function_info=function_info,
                    requirement=requirement,
                )
            )

        return results
