"""
src/agents/agent2_test_validation.py
──────────────────────────────────────
Agent 2 — Test Validation, Traceability and Repair

Three checks in order:
1. Traceability — does the code cover all specified test cases?
2. AST parse    — is it valid Python syntax?
3. pytest dry run — does it collect without import errors?

If any check fails, sends the exact error to the LLM for repair.
Repeats up to max_repair_iterations times.
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from src.utils.llm import build_groq_llm
from src.models.schemas import (
    RawTestOutput,
    ValidatedTestOutput,
    RepairIteration,
    RepairStatus,
    TraceabilityReport,
    TraceabilityEntry,
    TestCaseSet,
)
from src.rag.retriever import RepositoryRetriever
from src.utils.ast_utils import (
    ast_parse_check,
    pytest_dry_run,
    extract_imports,
    extract_test_functions,
    strip_code_fences,
)

logger = logging.getLogger(__name__)


# ── Prompts ────────────────────────────────────────────────────────────────────

REPAIR_SYSTEM = """You are an expert Python engineer specialising in
fixing broken pytest test code.

You will be given:
1. A broken pytest test file
2. The exact error message explaining what is wrong
3. The original source code being tested
4. Project context showing what imports and classes actually exist

Your job is to return a FIXED version of the test file.

Rules:
1. Only fix the specific error — do not rewrite everything
2. Only use imports that exist in the project context
3. Keep all the original test functions
4. Return ONLY the fixed Python code, no explanations, no markdown fences"""


TRACEABILITY_REPAIR_SYSTEM = """You are an expert Python engineer.
You will be given pytest test code that is missing implementations
for some test cases.

Your job is to ADD the missing test functions to the existing code.
Do NOT remove or change any existing test functions.
Return the COMPLETE test file with the missing tests added.
Return ONLY the Python code, no explanations, no markdown fences."""


def _build_repair_prompt(
    broken_code: str,
    error_type: str,
    error_message: str,
    original_source: str,
    rag_context: str,
) -> str:
    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (real imports and classes that exist)
{rag_context}
"""
    return f"""## Broken Test Code
```python
{broken_code}
```

## Error
Type: {error_type}
Message: {error_message}

## Original Source Code Being Tested
```python
{original_source}
```
{context_section}
Fix the broken test code and return only the corrected Python."""


def _build_traceability_repair_prompt(
    current_code: str,
    missing_cases: list,
    original_source: str,
    rag_context: str,
) -> str:
    """Build prompt to add missing test case implementations."""
    missing_text = ""
    for tc in missing_cases:
        missing_text += f"""
{tc.test_case_id}: {tc.description}
  Input    : {tc.input_values if hasattr(tc, 'input_values') else 'N/A'}
  Expected : {tc.expected_output if hasattr(tc, 'expected_output') else 'N/A'}
"""

    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context
{rag_context}
"""

    return f"""## Existing Test Code
```python
{current_code}
```

## Missing Test Cases (ADD these to the existing code)
{missing_text}

## Original Source Code
```python
{original_source}
```
{context_section}
Add the missing test functions and return the complete test file."""


# ── Traceability Check ─────────────────────────────────────────────────────────

def _build_traceability_report(
    test_case_set: TestCaseSet,
    test_code: str,
) -> TraceabilityReport:
    """
    Check whether each test case has a corresponding test function.

    Strategy:
    1. Extract all test function names from the code using AST
    2. For each test case, check if any function name contains
       the test case ID (e.g. TC001 → test_tc001_...)
    3. Build a TraceabilityReport showing what is covered and what is missing
    """
    # Get all test function names from the generated code
    test_functions = extract_test_functions(test_code)
    test_functions_lower = [f.lower() for f in test_functions]

    entries = []
    for tc in test_case_set.test_cases:
        tc_id_lower = tc.test_case_id.lower().replace("-", "").replace("_", "")

        # Check if any test function references this test case ID
        matched_function = None
        for i, fn_lower in enumerate(test_functions_lower):
            fn_normalized = fn_lower.replace("_", "")
            if tc_id_lower in fn_normalized:
                matched_function = test_functions[i]
                break

        entries.append(TraceabilityEntry(
            test_case_id=tc.test_case_id,
            description=tc.description,
            implemented_by=matched_function,
            is_covered=matched_function is not None,
            notes=None if matched_function else "No matching test function found",
        ))

    return TraceabilityReport(
        segment_id=test_case_set.segment_id,
        function_name=test_case_set.function_name,
        entries=entries,
    )


# ── Main Agent Class ───────────────────────────────────────────────────────────

class Agent2TestValidation:
    """
    Agent 2 — Validation, Traceability and Repair

    Check 1: Traceability — are all test cases implemented?
    Check 2: AST parse — is it valid Python syntax?
    Check 3: pytest dry run — does it collect without errors?

    If any check fails, repairs using LLM + RAG context.
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.max_iterations = settings.max_repair_iterations
        self._repo_path = None
        self.llm = build_groq_llm(settings.groq_model_agent1, temperature=0.1)
        logger.info(f"Agent 2 ready | max_repairs={self.max_iterations}")

    def run(
        self,
        raw_output: RawTestOutput,
        original_segment_source: str,
        repo_path: str | None = None,
    ) -> ValidatedTestOutput:
        """
        Validate Agent 1's output.

        Args:
            raw_output: The RawTestOutput from Agent 1 (includes test_case_set)
            original_segment_source: The original source code being tested
            repo_path: Repository root, so the pytest dry run can import the
                       module under test

        Returns:
            ValidatedTestOutput with traceability report and repair history
        """
        self._repo_path = repo_path
        logger.info(
            f"Agent 2 validating | function={raw_output.function_name}"
        )

        # Handle empty output from Agent 1
        if not raw_output.raw_test_code.strip():
            logger.warning(
                f"Agent 1 returned empty code for {raw_output.function_name}"
            )
            return ValidatedTestOutput(
                segment_id=raw_output.segment_id,
                function_name=raw_output.function_name,
                file_path=raw_output.file_path,
                validated_test_code="",
                is_syntactically_valid=False,
                repair_status=RepairStatus.FAILED,
            )

        current_code = raw_output.raw_test_code
        repair_iterations = []
        repair_status = RepairStatus.NOT_ATTEMPTED
        traceability_report = None

        # ── Check 1: Traceability ──────────────────────────────────────────
        if raw_output.test_case_set and raw_output.test_case_set.test_cases:
            logger.info(
                f"Agent 2 traceability check | "
                f"test_cases={raw_output.test_case_set.total_test_cases}"
            )

            traceability_report = _build_traceability_report(
                raw_output.test_case_set,
                current_code,
            )

            logger.info(
                f"Traceability | covered={traceability_report.covered_count}/"
                f"{traceability_report.total_test_cases} | "
                f"rate={traceability_report.coverage_rate:.1%}"
            )

            # If any test cases are not covered, attempt to repair
            uncovered = [e for e in traceability_report.entries if not e.is_covered]

            if uncovered:
                logger.info(
                    f"Traceability gap: {len(uncovered)} test cases not implemented. "
                    f"Requesting repair."
                )

                # Get missing test case objects
                uncovered_ids = {e.test_case_id for e in uncovered}
                missing_cases = [
                    tc for tc in raw_output.test_case_set.test_cases
                    if tc.test_case_id in uncovered_ids
                ]

                rag_context = self.retriever.context_for_validation(
                    function_name=raw_output.function_name,
                    file_path=raw_output.file_path,
                    imports_in_test=extract_imports(current_code),
                )

                repair_prompt = _build_traceability_repair_prompt(
                    current_code=current_code,
                    missing_cases=missing_cases,
                    original_source=original_segment_source,
                    rag_context=rag_context,
                )

                messages = [
                    SystemMessage(content=TRACEABILITY_REPAIR_SYSTEM),
                    HumanMessage(content=repair_prompt),
                ]

                try:
                    response = self.llm.invoke(messages)
                    fixed_code = strip_code_fences(response.content)

                    if fixed_code:
                        current_code = fixed_code
                        repair_status = RepairStatus.SUCCESS

                        # Rebuild traceability report after repair
                        traceability_report = _build_traceability_report(
                            raw_output.test_case_set,
                            current_code,
                        )

                        repair_iterations.append(RepairIteration(
                            iteration=1,
                            error_type="TraceabilityGap",
                            error_message=f"{len(uncovered)} test cases not implemented: "
                                         f"{', '.join(e.test_case_id for e in uncovered)}",
                            repair_applied=True,
                        ))

                        logger.info(
                            f"Traceability repair done | "
                            f"now covered={traceability_report.covered_count}/"
                            f"{traceability_report.total_test_cases}"
                        )

                except Exception as e:
                    logger.error(f"Traceability repair failed: {e}")

        # ── Checks 2 & 3: AST + Dry Run Repair Loop ───────────────────────
        for iteration in range(self.max_iterations + 1):

            # AST check
            ast_result = ast_parse_check(current_code)
            if not ast_result.is_valid:
                logger.info(
                    f"AST check failed (iteration {iteration}) | "
                    f"error={ast_result.error_type}"
                )
                if iteration == self.max_iterations:
                    repair_status = RepairStatus.MAX_ITERATIONS
                    break

                fixed_code = self._repair(
                    broken_code=current_code,
                    error_type=ast_result.error_type,
                    error_message=ast_result.error_message,
                    original_source=original_segment_source,
                    function_name=raw_output.function_name,
                    file_path=raw_output.file_path,
                )

                repair_iterations.append(RepairIteration(
                    iteration=iteration + 1,
                    error_type=ast_result.error_type,
                    error_message=ast_result.error_message,
                    repair_applied=bool(fixed_code),
                ))

                if fixed_code:
                    current_code = fixed_code
                    repair_status = RepairStatus.SUCCESS
                continue

            # Dry run check
            dry_run = pytest_dry_run(current_code, repo_path=self._repo_path)
            if not dry_run.is_valid:
                logger.info(
                    f"Dry run failed (iteration {iteration}) | "
                    f"error={dry_run.error_type}"
                )
                if iteration == self.max_iterations:
                    repair_status = RepairStatus.MAX_ITERATIONS
                    break

                fixed_code = self._repair(
                    broken_code=current_code,
                    error_type=dry_run.error_type,
                    error_message=dry_run.error_message,
                    original_source=original_segment_source,
                    function_name=raw_output.function_name,
                    file_path=raw_output.file_path,
                )

                repair_iterations.append(RepairIteration(
                    iteration=iteration + 1,
                    error_type=dry_run.error_type,
                    error_message=dry_run.error_message,
                    repair_applied=bool(fixed_code),
                ))

                if fixed_code:
                    current_code = fixed_code
                    repair_status = RepairStatus.SUCCESS
                continue

            # Both passed
            logger.info(
                f"Agent 2 validation passed | "
                f"function={raw_output.function_name} | "
                f"tests_collected={dry_run.tests_collected} | "
                f"repairs={len(repair_iterations)}"
            )

            return ValidatedTestOutput(
                segment_id=raw_output.segment_id,
                function_name=raw_output.function_name,
                file_path=raw_output.file_path,
                validated_test_code=current_code,
                is_syntactically_valid=True,
                repair_status=repair_status,
                repair_iterations=repair_iterations,
                total_repairs=len(repair_iterations),
                traceability_report=traceability_report,
            )

        # Loop ended without passing
        logger.warning(
            f"Agent 2 could not fully validate {raw_output.function_name} "
            f"after {len(repair_iterations)} repairs"
        )

        return ValidatedTestOutput(
            segment_id=raw_output.segment_id,
            function_name=raw_output.function_name,
            file_path=raw_output.file_path,
            validated_test_code=current_code,
            is_syntactically_valid=False,
            repair_status=repair_status,
            repair_iterations=repair_iterations,
            total_repairs=len(repair_iterations),
            traceability_report=traceability_report,
        )

    def _repair(
        self,
        broken_code: str,
        error_type: str,
        error_message: str,
        original_source: str,
        function_name: str,
        file_path: str,
    ) -> str:
        """Send broken code + exact error to LLM and get a fix."""
        imports_in_test = extract_imports(broken_code)
        rag_context = self.retriever.context_for_validation(
            function_name=function_name,
            file_path=file_path,
            imports_in_test=imports_in_test,
        )

        prompt = _build_repair_prompt(
            broken_code=broken_code,
            error_type=error_type,
            error_message=error_message,
            original_source=original_source,
            rag_context=rag_context,
        )

        messages = [
            SystemMessage(content=REPAIR_SYSTEM),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            return strip_code_fences(response.content)
        except Exception as e:
            logger.error(f"Repair LLM call failed: {e}")
            return ""