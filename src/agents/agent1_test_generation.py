"""
src/agents/agent1_test_generation.py
──────────────────────────────────────
Agent 1 — Two-Phase Test Generation

Phase A: Generate test case specifications (plain language)
         What to test, not how to test it.

Phase B: Generate pytest test code from those specifications
         Using the test cases as a blueprint.

This two-phase approach:
- Produces traceable test cases (research contribution)
- Reduces hallucination (code follows a clear spec)
- Improves coverage (reasoning about cases before coding)
"""

import json
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
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


# ── Phase A Prompts ────────────────────────────────────────────────────────────

PHASE_A_SYSTEM = """You are an expert software testing engineer.
Your job is to analyse a Python function and identify all the test cases needed
to thoroughly test it. You do NOT write code yet — only specifications.

Think step by step:
- What does this function do?
- What are the normal/happy path cases?
- What are the edge cases (boundary values, empty inputs, zero)?
- What are the negative cases (wrong types, invalid values)?
- What exceptions should be raised and when?

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
Return valid JSON only. No markdown. No explanation."""


def _build_phase_a_prompt(
    segment: HighRiskSegment,
    rag_context: str,
) -> str:
    """Build the Phase A prompt for test case specification."""

    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (how this function is used in the codebase)
{rag_context}
"""

    return f"""## Function to Analyse

File: {segment.file_path}
Function: {segment.function_name}
Risk Score: {segment.risk_score:.2f} (higher = more likely to have bugs)
Cyclomatic Complexity: {segment.cyclomatic_complexity or 'N/A'}
{context_section}
## Source Code
```python
{segment.source_code}
```

Identify all test cases needed for this function.
Be thorough — cover normal cases, edge cases, negative cases, and exceptions.
Return only the JSON object."""


# ── Phase B Prompts ────────────────────────────────────────────────────────────

PHASE_B_SYSTEM = """You are an expert Python software engineer specialising
in writing pytest unit tests.

You will be given:
1. A Python function to test
2. A list of test case specifications (what to test)
3. Project context (real imports and classes that exist)

Your job is to implement EVERY test case as a pytest function.

Rules:
1. Implement ALL test cases — do not skip any
2. Name each test function to match its test case (e.g. TC001 → test_tc001_...)
3. Only use imports that exist in the project context
4. Always import pytest at the top
5. Use pytest.raises() for exception test cases
6. Return ONLY the Python test code, no explanations, no markdown fences"""


def _build_phase_b_prompt(
    segment: HighRiskSegment,
    test_case_set: TestCaseSet,
    rag_context: str,
) -> str:
    """Build the Phase B prompt for test code generation."""

    # Format test cases as a clear numbered list
    test_cases_text = ""
    for tc in test_case_set.test_cases:
        test_cases_text += f"""
{tc.test_case_id} [{tc.category.value.upper()}]: {tc.description}
  Input    : {tc.input_values}
  Expected : {tc.expected_output}
"""

    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (use these for correct imports)
{rag_context}
"""

    return f"""## Function to Test

File: {segment.file_path}
Function: {segment.function_name}
{context_section}
## Source Code
```python
{segment.source_code}
```

## Test Case Specifications (implement ALL of these)
{test_cases_text}

Implement every test case above as a pytest function.
Name format: test_tc001_description, test_tc002_description etc.
Return only the Python test code."""


# ── Helper: Parse Phase A JSON ─────────────────────────────────────────────────

def _parse_test_cases(
    raw_json: str,
    segment_id: str,
    function_name: str,
) -> TestCaseSet:
    """
    Parse the LLM's JSON response from Phase A into a TestCaseSet.
    Falls back to an empty set if parsing fails.
    """
    try:
        # Strip markdown fences if present
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
                    test_case_id=tc.get("test_case_id", f"TC{len(test_cases)+1:03d}"),
                    description=tc.get("description", ""),
                    input_values=tc.get("input_values", ""),
                    expected_output=tc.get("expected_output", ""),
                    category=TestCaseCategory(tc.get("category", "normal")),
                ))
            except Exception as e:
                logger.warning(f"Skipping malformed test case: {e}")
                continue

        logger.info(
            f"Phase A parsed {len(test_cases)} test cases "
            f"for {function_name}"
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
    Agent 1 — Two-Phase Test Generation

    Phase A: Identifies WHAT to test (test case specifications)
    Phase B: Implements HOW to test it (pytest code from specs)
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model_agent1,
            temperature=0.2,
        )
        logger.info(f"Agent 1 ready | model={settings.groq_model_agent1}")

    def run(self, segment: HighRiskSegment) -> RawTestOutput:
        """
        Run the two-phase test generation.

        Phase A: Generate test case specifications
        Phase B: Generate pytest code from those specifications

        Returns RawTestOutput containing both the test cases
        and the generated code.
        """
        logger.info(
            f"Agent 1 starting | function={segment.function_name}"
        )

        # ── Phase A: Generate Test Case Specifications ─────────────────────
        logger.info(f"Agent 1 Phase A — generating test cases for {segment.function_name}")

        # Get RAG context for Phase A
        rag_context_a = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        phase_a_prompt = _build_phase_a_prompt(segment, rag_context_a)

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
                f"Agent 1 Phase A done | "
                f"test_cases={test_case_set.total_test_cases} | "
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

        # If Phase A produced no test cases, fall back gracefully
        if not test_case_set.test_cases:
            logger.warning(
                f"Phase A returned 0 test cases for {segment.function_name}. "
                f"Falling back to direct generation."
            )
            return self._direct_generation(segment)

        # ── Phase B: Generate Test Code from Specifications ────────────────
        logger.info(
            f"Agent 1 Phase B — generating test code from "
            f"{test_case_set.total_test_cases} test cases"
        )

        # Get RAG context for Phase B (same retriever, slightly different query)
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
                f"Agent 1 Phase B done | "
                f"function={segment.function_name} | "
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
        """
        Fallback if Phase A fails to produce test cases.
        Generates code directly without specifications.
        """
        logger.info(
            f"Agent 1 direct generation fallback for {segment.function_name}"
        )
        rag_context = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        prompt = f"""Write comprehensive pytest tests for this function:

```python
{segment.source_code}
```

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
            logger.error(f"Direct generation also failed: {e}")
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code="",
                test_case_set=None,
            )