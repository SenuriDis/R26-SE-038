"""
Parses requirement documents supplied as JSON.

Accepts either a single requirement object or a list of them:

{
  "function_name": "calculate_fee",
  "inputs": [{"name": "days", "constraint": ">=0"}],
  "expected_output": "fee amount",
  "exceptions": ["ValueError"]
}
"""

import json
from typing import List

from .base_parser import RequirementParser
from ..models import InputConstraint, Requirement


class JsonRequirementParser(RequirementParser):
    def parse(self, file_path: str) -> List[Requirement]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self._fail(file_path, f"invalid JSON ({e})")
        except OSError as e:
            self._fail(file_path, str(e))

        records = data if isinstance(data, list) else [data]
        return [self._parse_record(record, file_path, i) for i, record in enumerate(records)]

    def _parse_record(self, record: dict, file_path: str, index: int) -> Requirement:
        if "function_name" not in record:
            self._fail(file_path, f"record {index} missing 'function_name'")

        inputs = [
            InputConstraint(name=inp.get("name", ""), constraint=inp.get("constraint", ""))
            for inp in record.get("inputs", [])
        ]

        return Requirement(
            function_name=record["function_name"],
            inputs=inputs,
            expected_output=record.get("expected_output", ""),
            exceptions=list(record.get("exceptions", [])),
        )
