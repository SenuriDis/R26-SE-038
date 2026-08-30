import json
import logging
import subprocess
import sys
import tempfile
import os
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from src.utils.llm import build_groq_llm
from src.models.schemas import (
    HighRiskSegment,
    CodeReviewReport,
    ReviewFinding,
    ReviewCategory,
    Severity,
)
from src.rag.retriever import RepositoryRetriever

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior Python software engineer performing 
a thorough code quality review.

You will be given:
1. A Python function to review
2. Its pylint analysis output
3. Project context showing how this function fits into the larger system

Your job is to identify real issues — not theoretical ones.
Use the project context to avoid false positives.

You must respond with ONLY a valid JSON object in this exact format:
{
    "summary": "one paragraph summary of overall code quality",
    "findings": [
        {
            "finding_id": "F001",
            "category": "bug|code_smell|solid_violation|maintainability|security",
            "severity": "critical|high|medium|low|info",
            "line_number": 12,
            "description": "clear description of the issue",
            "suggested_fix": "concrete suggestion to fix it"
        }
    ]
}

Rules:
- Only report real issues you are confident about
- Use project context before flagging something as a violation
- Keep descriptions concise and actionable
- suggested_fix must be a concrete code suggestion, not vague advice
- Return valid JSON only, no markdown, no explanation"""


def _run_pylint(source_code: str, file_path: str) -> str:
    """
    Run pylint on the source code and return its output.
    We write to a temp file because pylint needs a real file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="agent3_pylint_",
        delete=False,
    ) as tmp:
        tmp.write(source_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pylint",
                tmp_path,
                "--output-format=text",
                "--score=yes",
                "--disable=C0114,C0115,C0116",  # Ignore missing docstring warnings
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr

        # Extract the pylint score
        score = None
        for line in output.splitlines():
            if "Your code has been rated at" in line:
                try:
                    score_str = line.split("rated at")[1].split("/")[0].strip()
                    score = float(score_str)
                except Exception:
                    pass

        return output, score

    except subprocess.TimeoutExpired:
        return "pylint timed out", None
    except Exception as e:
        return f"pylint error: {e}", None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _build_prompt(
    segment: HighRiskSegment,
    pylint_output: str,
    rag_context: str,
) -> str:
    """Build the review prompt with code, pylint output and RAG context."""

    context_section = ""
    if rag_context:
        context_section = f"""
## Project Context (callers, dependencies, class hierarchy)
{rag_context}
"""

    return f"""## Code to Review

File: {segment.file_path}
Function: {segment.function_name}
Risk Score: {segment.risk_score:.2f}
{context_section}
## Source Code
```python
{segment.source_code}
```

## Pylint Analysis
{pylint_output}

Review this code and return your findings as a JSON object."""


def _parse_findings(raw_json: str) -> tuple[list[ReviewFinding], str]:
    """
    Parse the LLM's JSON response into ReviewFinding objects.
    Returns (findings, summary).
    """
    try:
        # Sometimes the LLM wraps in markdown fences anywayj
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        raw_json = raw_json.strip()

        data = json.loads(raw_json)
        summary = data.get("summary", "No summary provided")
        raw_findings = data.get("findings", [])

        findings = []
        for i, f in enumerate(raw_findings):
            try:
                finding = ReviewFinding(
                    finding_id=f.get("finding_id", f"F{i+1:03d}"),
                    category=ReviewCategory(
                        f.get("category", "maintainability")
                    ),
                    severity=Severity(f.get("severity", "low")),
                    line_number=f.get("line_number"),
                    description=f.get("description", ""),
                    suggested_fix=f.get("suggested_fix", ""),
                )
                findings.append(finding)
            except Exception as e:
                logger.warning(f"Skipping malformed finding: {e}")
                continue

        return findings, summary

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Agent 3 JSON response: {e}")
        return [], "Could not parse review output"


class Agent3CodeReview:
    """
    Agent 3 - Code Review

    Performs RAG-augmented semantic code review of high-risk segments.
    Detects code smells, SOLID violations, bugs and maintainability issues.
    Uses pylint as an additional signal alongside LLM reasoning.
    """

    def __init__(self, retriever: RepositoryRetriever):
        self.retriever = retriever
        self.llm = build_groq_llm(settings.groq_model_agent3, temperature=0.1)
        logger.info(f"Agent 3 ready | model={settings.groq_model_agent3}")

    def run(self, segment: HighRiskSegment) -> CodeReviewReport:
        """
        Perform code review on the given high-risk segment.

        Args:
            segment: The high-risk code segment from Component 2

        Returns:
            CodeReviewReport with all findings and a summary
        """
        logger.info(
            f"Agent 3 reviewing | function={segment.function_name}"
        )

        # Step 1: Run pylint for structured static analysis
        pylint_output, pylint_score = _run_pylint(
            segment.source_code,
            segment.file_path,
        )

        # Step 2: Get RAG context - callers, dependencies, class hierarchy
        rag_context = self.retriever.context_for_code_review(
            function_name=segment.function_name,
            file_path=segment.file_path,
        )

        # Step 3: Build prompt and call LLM
        prompt = _build_prompt(segment, pylint_output, rag_context)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            raw_response = response.content

            # Step 4: Parse the JSON response into structured findings
            findings, summary = _parse_findings(raw_response)

            usage = response.response_metadata.get("token_usage", {})

            logger.info(
                f"Agent 3 done | function={segment.function_name} "
                f"| findings={len(findings)} | pylint={pylint_score}"
            )

            return CodeReviewReport(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                findings=findings,
                pylint_score=pylint_score,
                summary=summary,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

        except Exception as e:
            logger.error(
                f"Agent 3 failed for {segment.function_name}: {e}"
            )
            return CodeReviewReport(
                segment_id=segment.segment_id,
                function_name=segment.function_name,
                file_path=segment.file_path,
                findings=[],
                summary=f"Review failed: {e}",
            )