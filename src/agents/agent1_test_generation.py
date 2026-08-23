import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from src.models.schemas import HighRiskSegment, RawTestOutput
from src.rag.retriever import RepositoryRetriever
from src.utils.ast_utils import strip_code_fences

logger = logging.getLogger(__name__)


# ─ Prompts 

SYSTEM_PROMPT = """You are an expert Python software engineer specialising in 
writing pytest unit tests. Your job is to write thorough, executable pytest 
test cases for the Python function you are given.

You must follow these rules:
1. Only import modules that actually exist in the project context provided
2. Always import pytest at the top
3. Write test function names starting with test_
4. Include normal cases, edge cases, and negative cases
5. Use pytest.raises() for testing exceptions
6. Never invent class names or method names that are not in the code or context
7. Return ONLY the Python test code, no explanations, no markdown fences

Think step by step:
- What does this function do?
- What are the expected inputs and outputs?
- What edge cases could cause problems?
- What should raise exceptions?
Then write the tests."""


def _build_prompt(
    segment: HighRiskSegment,
    rag_context: str,
) -> str:
    """
    Build the human message prompt for Agent 1.
    Combines the function code, risk score, and RAG context.
    """
    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (use this to write correct imports and references)
{rag_context}
"""

    return f"""## Function to Test

File: {segment.file_path}
Function: {segment.function_name}
Risk Score: {segment.risk_score:.2f} (higher = more likely to have bugs)
Cyclomatic Complexity: {segment.cyclomatic_complexity or 'N/A'}
{context_section}
## Source Code
```python
{segment.source_code}
```

Now write comprehensive pytest test cases for this function.
Remember: only use imports and classes that exist in the project context above.
Return only the Python test code."""


class Agent1TestGeneration:
    """
    Agent 1 - Test Generation

    Takes a high-risk code segment and generates pytest test cases
    using chain-of-thought prompting enriched with RAG context.
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model_agent1,
            temperature=0.2,  # Low temperature = more consistent, less random
        )
        logger.info(f"Agent 1 ready | model={settings.groq_model_agent1}")

    def run(self, segment: HighRiskSegment) -> RawTestOutput:
        """
        Generate pytest test cases for the given high-risk segment.

        Args:
            segment: The high-risk code segment from Component 2

        Returns:
            RawTestOutput containing the generated test code
        """
        logger.info(
            f"Agent 1 generating tests | function={segment.function_name}"
        )

        # Step 1: Get relevant context from ChromaDB
        rag_context = self.retriever.context_for_test_generation(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )
        rag_used = bool(rag_context)

        # Step 2: Build the prompt
        human_prompt = _build_prompt(segment, rag_context)

        # Step 3: Call the LLM
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            raw_code = response.content

            # Step 4: Clean up any markdown fences the LLM added
            clean_code = strip_code_fences(raw_code)

            # Step 5: Track token usage
            usage = response.response_metadata.get("token_usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            logger.info(
                f"Agent 1 done | function={segment.function_name} "
                f"| tokens={prompt_tokens + completion_tokens}"
            )

            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code=clean_code,
                rag_context_used=rag_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        except Exception as e:
            logger.error(
                f"Agent 1 failed for {segment.function_name}: {e}"
            )
            # Return empty output so the pipeline can continue
            # with other segments rather than crashing completely
            return RawTestOutput(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                raw_test_code="",
                rag_context_used=rag_used,
            )