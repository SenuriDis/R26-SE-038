"""
src/agents/agent1_test_generation.py
──────────────────────────────────────
Agent 1 — Two-Phase Test Generation with ML-Guided Depth

Phase A: Generate test case specifications guided by ML risk signals
         - Uses tier (HIGH/MEDIUM/LOW) to determine depth
         - Uses ML explanation to focus on risky areas
         - Uses recommended test types from Component 2

Phase B: Generate pytest test code from those specifications
         - Each test case becomes a named pytest function
         - RAG context prevents hallucinated imports
"""

import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from src.utils.llm import build_groq_llm
from src.models.schemas import (
    HighRiskSegment,
    RawTestOutput,
    TestCase,
    TestCaseSet,
    TestCaseCategory,
)
from src.rag.retriever import RepositoryRetriever
from src.utils.ast_utils import strip_code_fences

logger = logging.getLogger(__name__)


def _module_import_path(file_path: str) -> str:
    """
    Turn a repo-relative file path into a Python import path.
    e.g. 'src/payment.py' -> 'src.payment'
    """
    p = file_path.replace("\\", "/").strip("/")
    if p.endswith(".py"):
        p = p[:-3]
    return p.replace("/", ".")


# ── Phase A Prompts ────────────────────────────────────────────────────────────

PHASE_A_SYSTEM = """You are an expert software testing engineer.
Your job is to analyse a Python function and identify test cases needed
to thoroughly test it based on its risk level.

You must respond with ONLY a valid JSON object in this exact format:
{
    "test_cases": [
        {
            "test_case_id": "TC001",
            "description": "Normal case - divide two positive integers",
            "input_values": "a=10, b=2",
            "expected_output": "returns 5.0",
            "category": "normal"
        }
    ]
}

Categories must be one of: normal, edge, negative, exception
Return valid JSON only. No markdown. No explanation outside the JSON."""


def _build_phase_a_prompt(
    segment: HighRiskSegment,
    rag_context: str,
    risk_level: str = "MEDIUM",
    test_depth: str = "boundary",
    min_test_cases: int = 6,
    test_types: list[str] = None,
    explanation_text: str = "",
    top_risk_factors: list[dict] = None,
) -> str:
    """
    Build Phase A prompt with ML signals injected.
    The depth and focus of test case generation varies by tier.
    """

    if test_types is None:
        test_types = ["normal", "edge"]
    if top_risk_factors is None:
        top_risk_factors = []

    # Build tier-specific instructions
    if risk_level == "HIGH":
        depth_instruction = f"""This function is HIGH RISK.
Generate AT LEAST {min_test_cases} test cases covering ALL of these types:
- Normal cases (happy path)
- Edge cases (boundary values, empty inputs, zero, None)
- Negative cases (invalid inputs, wrong types)
- Exception cases (what should raise errors and when)
Be exhaustive. Cover every code path."""

    elif risk_level == "MEDIUM":
        depth_instruction = f"""This function is MEDIUM RISK.
Generate AT LEAST {min_test_cases} test cases focusing on:
- Normal cases (happy path)
- Edge cases (boundary values)
- Boundary tests (min/max values, limits)
Focus on boundary conditions and typical usage."""

    else:  # LOW
        depth_instruction = f"""This function is LOW RISK.
Generate AT LEAST {min_test_cases} test cases covering:
- Normal cases (happy path)
- Basic usage scenarios
Keep it simple and focused on correct behaviour."""

    # Build ML risk context section
    ml_context = ""
    if explanation_text:
        ml_context += f"\n## Why This Function is Risky (ML Analysis)\n{explanation_text}\n"

    if top_risk_factors:
        ml_context += "\n## Top Risk Factors to Focus Tests On\n"
        for factor in top_risk_factors[:3]:
            feature = factor.get("feature", "").replace("_", " ").title()
            direction = factor.get("direction", "increases")
            ml_context += f"- {feature} ({direction} risk)\n"

    # Build test types section
    types_str = ", ".join(test_types)

    # Build RAG context section
    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (how this function is used in the codebase)
{rag_context}"""

    return f"""## Function to Analyse

File: {segment.file_path}
Function: {segment.function_name}
Risk Level: {risk_level}
Risk Score: {segment.risk_score:.3f}
Cyclomatic Complexity: {segment.cyclomatic_complexity or 'N/A'}
{ml_context}
## Testing Instructions
{depth_instruction}

Focus test types: {types_str}
{context_section}

## Source Code
```python
{segment.source_code}
```

Identify all test cases. Return only the JSON object."""


# ── Phase B Prompts ────────────────────────────────────────────────────────────

PHASE_B_SYSTEM = """You are an expert Python software engineer specialising
in writing pytest unit tests.

You will be given:
1. A Python function to test
2. A list of test case specifications
3. Project context with real imports and classes

Your job is to implement EVERY test case as a pytest function.

Rules:
1. Implement ALL test cases — do not skip any
2. Name each function: test_tc001_short_description
3. Only use imports that exist in the project context
4. Always import pytest at the top
5. Use pytest.raises() for exception cases
6. Return ONLY the Python test code, no markdown, no explanation"""


def _build_phase_b_prompt(
    segment: HighRiskSegment,
    test_case_set: TestCaseSet,
    rag_context: str,
) -> str:
    """Build Phase B prompt — implement test cases as pytest code."""

    test_cases_text = ""
    for tc in test_case_set.test_cases:
        test_cases_text += (
            f"\n{tc.test_case_id} [{tc.category.value.upper()}]: "
            f"{tc.description}\n"
            f"  Input    : {tc.input_values}\n"
            f"  Expected : {tc.expected_output}\n"
        )

    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (use for correct imports)
{rag_context}"""

    import_path = _module_import_path(segment.file_path)

    return f"""## Function to Test

File: {segment.file_path}
Function: {segment.function_name}
{context_section}

## Import Requirement
The function under test lives at `{segment.file_path}`, which is importable
from the repository root. Import it with exactly:

    from {import_path} import {segment.function_name}

Do NOT invent any other module path and do NOT use relative imports.

## Source Code
```python
{segment.source_code}
```

## Test Case Specifications — implement ALL of these
{test_cases_text}

Implement every test case as a pytest function.
Naming: test_tc001_description, test_tc002_description etc.
Return only the Python test code."""


# ── Helper: Parse Phase A JSON ─────────────────────────────────────────────────

def _parse_test_cases(
    raw_json: str,
    segment_id: str,
    function_name: str,
) -> TestCaseSet:
    """Parse Phase A JSON response into a TestCaseSet."""
    try:
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        raw_json = raw_json.strip()

        data = json.loads(raw_json)
        raw_cases = data.get("test_cases", [])

        test_cases = []
        for tc in raw_cases:
            try:
                test_cases.append(TestCase(
                    test_case_id=tc.get(
                        "test_case_id",
                        f"TC{len(test_cases)+1:03d}"
                    ),
                    description=tc.get("description", ""),
                    input_values=tc.get("input_values", ""),
                    expected_output=tc.get("expected_output", ""),
                    category=TestCaseCategory(tc.get("category", "normal")),
                ))
            except Exception as e:
                logger.warning(f"Skipping malformed test case: {e}")

        logger.info(
            f"Phase A parsed {len(test_cases)} test cases for {function_name}"
        )

        return TestCaseSet(
            segment_id=segment_id,
            function_name=function_name,
            test_cases=test_cases,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Phase A JSON: {e}")
        return TestCaseSet(
            segment_id=segment_id,
            function_name=function_name,
            test_cases=[],
        )


# ── Main Agent Class ───────────────────────────────────────────────────────────

class Agent1TestGeneration:
    """
    Agent 1 — Two-Phase ML-Guided Test Generation

    Phase A: Identifies WHAT to test using ML risk signals
    Phase B: Implements HOW to test using pytest
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.llm = build_groq_llm(settings.groq_model_agent1, temperature=0.2)
        logger.info(f"Agent 1 ready | model={settings.groq_model_agent1}")

    def run(
        self,
        segment: HighRiskSegment,
        risk_level: str = "MEDIUM",
        test_depth: str = "boundary",
        min_test_cases: int = 6,
        test_types: list[str] = None,
        explanation_text: str = "",
        top_risk_factors: list[dict] = None,
    ) -> RawTestOutput:
        """
        Run two-phase test generation with ML-guided depth.

        Args:
            segment: The high-risk code segment
            risk_level: HIGH / MEDIUM / LOW from Component 2
            test_depth: exhaustive / boundary / basic
            min_test_cases: Minimum number of test cases to generate
            test_types: Categories of tests to focus on
            explanation_text: ML explanation of why function is risky
            top_risk_factors: ML feature contributions

        Returns:
            RawTestOutput with test cases and generated code
        """
        if test_types is None:
            test_types = ["normal", "edge"]
        if top_risk_factors is None:
            top_risk_factors = []

        logger.info(
            f"Agent 1 starting | function={segment.function_name} | "
            f"tier={risk_level} | depth={test_depth} | "
            f"min_cases={min_test_cases}"
        )

        # ── Phase A: Generate Test Case Specifications ─────────────────────
        logger.info(
            f"Agent 1 Phase A — generating test cases | "
            f"function={segment.function_name}"
        )

        rag_context_a = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        phase_a_prompt = _build_phase_a_prompt(
            segment=segment,
            rag_context=rag_context_a,
            risk_level=risk_level,
            test_depth=test_depth,
            min_test_cases=min_test_cases,
            test_types=test_types,
            explanation_text=explanation_text,
            top_risk_factors=top_risk_factors,
        )

        messages_a = [
            SystemMessage(content=PHASE_A_SYSTEM),
            HumanMessage(content=phase_a_prompt),
        ]

        try:
            response_a = self.llm.invoke(messages_a)
            test_case_set = _parse_test_cases(
                response_a.content,
                segment.segment_id,
                segment.function_name,
            )

            usage_a = response_a.response_metadata.get("token_usage", {})
            prompt_tokens = usage_a.get("prompt_tokens", 0)
            completion_tokens = usage_a.get("completion_tokens", 0)

            logger.info(
                f"Phase A done | test_cases={test_case_set.total_test_cases} | "
                f"tokens={prompt_tokens + completion_tokens}"
            )

        except Exception as e:
            logger.error(f"Agent 1 Phase A failed: {e}")
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code="",
                test_case_set=None,
                rag_context_used=bool(rag_context_a),
            )

        # Fallback if Phase A produced nothing
        if not test_case_set.test_cases:
            logger.warning(
                f"Phase A returned 0 test cases for {segment.function_name}. "
                f"Falling back to direct generation."
            )
            return self._direct_generation(segment)

        # ── Phase B: Generate Test Code ────────────────────────────────────
        logger.info(
            f"Agent 1 Phase B — generating code from "
            f"{test_case_set.total_test_cases} test cases"
        )

        rag_context_b = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        phase_b_prompt = _build_phase_b_prompt(
            segment, test_case_set, rag_context_b
        )

        messages_b = [
            SystemMessage(content=PHASE_B_SYSTEM),
            HumanMessage(content=phase_b_prompt),
        ]

        try:
            response_b = self.llm.invoke(messages_b)
            raw_code = strip_code_fences(response_b.content)

            usage_b = response_b.response_metadata.get("token_usage", {})
            prompt_tokens += usage_b.get("prompt_tokens", 0)
            completion_tokens += usage_b.get("completion_tokens", 0)

            logger.info(
                f"Phase B done | function={segment.function_name} | "
                f"total_tokens={prompt_tokens + completion_tokens}"
            )

            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code=raw_code,
                test_case_set=test_case_set,
                rag_context_used=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        except Exception as e:
            logger.error(f"Agent 1 Phase B failed: {e}")
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code="",
                test_case_set=test_case_set,
                rag_context_used=True,
            )

    def _direct_generation(self, segment: HighRiskSegment) -> RawTestOutput:
        """Fallback if Phase A fails."""
        logger.info(f"Direct generation fallback for {segment.function_name}")

        rag_context = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        import_path = _module_import_path(segment.file_path)

        prompt = f"""Write comprehensive pytest tests for this function:

```python
{segment.source_code}
```

Import the function under test with exactly:
    from {import_path} import {segment.function_name}

Project context:
{rag_context}

Return only the Python test code."""

        messages = [
            SystemMessage(content=PHASE_B_SYSTEM),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code=strip_code_fences(response.content),
                test_case_set=None,
                rag_context_used=bool(rag_context),
            )
        except Exception as e:
            logger.error(f"Direct generation failed: {e}")
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code="",
                test_case_set=None,
            )