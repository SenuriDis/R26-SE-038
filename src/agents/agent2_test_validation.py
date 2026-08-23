import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from src.models.schemas import (
    RawTestOutput,
    ValidatedTestOutput,
    RepairIteration,
    RepairStatus,
)
from src.rag.retriever import RepositoryRetriever
from src.utils.ast_utils import (
    ast_parse_check,
    pytest_dry_run,
    extract_imports,
    strip_code_fences,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert Python engineer specialising in 
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


def _build_repair_prompt(
    broken_code: str,
    error_type: str,
    error_message: str,
    original_source: str,
    rag_context: str,
) -> str:
    """Build the repair prompt with full context about what went wrong."""

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


class Agent2TestValidation:
    """
    Agent 2 - Test Validation and Repair

    Validates the test code from Agent 1 using AST checks
    and pytest dry runs. If broken, sends it to the LLM
    with the exact error message and attempts a repair.
    Repeats up to max_repair_iterations times.
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.max_iterations = settings.max_repair_iterations

        # Using Groq for repair - same model as Agent 1
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model_agent1,
            temperature=0.1,  # Very low - we want precise fixes not creativity
        )
        logger.info(f"Agent 2 ready | max_repairs={self.max_iterations}")

    def run(
        self,
        raw_output: RawTestOutput,
        original_segment_source: str,
    ) -> ValidatedTestOutput:
        """
        Validate and if necessary repair the test code from Agent 1.

        Args:
            raw_output: The RawTestOutput from Agent 1
            original_segment_source: The original source code being tested
                                     (needed for the repair prompt)

        Returns:
            ValidatedTestOutput with the final test code and repair history
        """
        logger.info(
            f"Agent 2 validating | function={raw_output.function_name}"
        )

        # If Agent 1 returned empty code, nothing to validate
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

        # Run the validation + repair loop
        for iteration in range(self.max_iterations + 1):

            # ─ Step 1: AST parse check 
            ast_result = ast_parse_check(current_code)

            if not ast_result.is_valid:
                logger.info(
                    f"AST check failed (iteration {iteration}) | "
                    f"error={ast_result.error_type}"
                )

                if iteration == self.max_iterations:
                    repair_status = RepairStatus.MAX_ITERATIONS
                    break

                # Attempt repair
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

            # ─ Step 2: pytest dry run 
            dry_run = pytest_dry_run(current_code)

            if not dry_run.is_valid:
                logger.info(
                    f"Dry run failed (iteration {iteration}) | "
                    f"error={dry_run.error_type}"
                )

                if iteration == self.max_iterations:
                    repair_status = RepairStatus.MAX_ITERATIONS
                    break

                # Attempt repair
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

            # ─ Both checks passed 
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
            )

        # Loop ended without passing — return best effort
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
        """
        Send broken test code to the LLM with the error details
        and get back a fixed version.
        """
        # Get context to help fix import errors
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
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            return strip_code_fences(response.content)
        except Exception as e:
            logger.error(f"Repair LLM call failed: {e}")
            return ""