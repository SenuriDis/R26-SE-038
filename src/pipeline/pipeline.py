import logging
import uuid
from pathlib import Path

from src.models.schemas import (
    PipelineInput,
    PipelineOutput,
    ValidatedTestOutput,
    CodeReviewReport,
    RepairStatus,
)
from src.rag.indexer import RepositoryIndexer
from src.rag.retriever import RepositoryRetriever
from src.agents.agent1_test_generation import Agent1TestGeneration
from src.agents.agent2_test_validation import Agent2TestValidation
from src.agents.agent3_code_review import Agent3CodeReview

logger = logging.getLogger(__name__)


class TestingPipeline:
    """
    The main pipeline for Component 3.

    Orchestrates the RAG indexer and all three agents to process
    high-risk code segments and produce validated tests and
    code review reports.
    """

    def __init__(self, force_reindex: bool = False):
        """
        Args:
            force_reindex: If True, rebuilds the ChromaDB index
                           from scratch even if one already exists.
        """
        self.force_reindex = force_reindex
        logger.info("TestingPipeline initialised")

    def run(self, pipeline_input: PipelineInput) -> PipelineOutput:
        """
        Run the full pipeline on the given input.

        Args:
            pipeline_input: Segments from Component 2 + repository path

        Returns:
            PipelineOutput with all validated tests and review reports
        """
        logger.info(
            f"Pipeline starting | run_id={pipeline_input.run_id} | "
            f"segments={len(pipeline_input.segments)}"
        )

        validated_tests = []
        code_review_reports = []
        errors = []

        # ── Step 1: Build the RAG index ───────────────────────────────────
        try:
            logger.info("Building RAG index...")
            indexer = RepositoryIndexer(pipeline_input.repository_path)
            index = indexer.build_index(force_rebuild=self.force_reindex)
            retriever = RepositoryRetriever(index)
            stats = indexer.get_stats()
            logger.info(f"RAG index ready | chunks={stats['total_chunks']}")
        except Exception as e:
            error_msg = f"RAG indexing failed: {e}"
            logger.error(error_msg)
            return PipelineOutput(
                run_id=pipeline_input.run_id,
                repository_path=pipeline_input.repository_path,
                segments_processed=0,
                segments_with_valid_tests=0,
                errors=[error_msg],
            )

        # ── Step 2: Initialise agents ─────────────────────────────────────
        agent1 = Agent1TestGeneration(retriever)
        agent2 = Agent2TestValidation(retriever)
        agent3 = Agent3CodeReview(retriever)

        # ── Step 3: Process each segment ─────────────────────────────────
        for i, segment in enumerate(pipeline_input.segments):
            logger.info(
                f"Processing segment {i+1}/{len(pipeline_input.segments)} "
                f"| function={segment.function_name}"
            )

            # Agent 1 → Agent 2 (test generation + validation)
            try:
                raw_output = agent1.run(segment)
                validated = agent2.run(raw_output, segment.source_code)
                validated_tests.append(validated)
            except Exception as e:
                error_msg = (
                    f"Test generation failed for "
                    f"{segment.function_name}: {e}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

            # Agent 3 (code review - independent of Agent 1/2)
            try:
                review = agent3.run(segment)
                code_review_reports.append(review)
            except Exception as e:
                error_msg = (
                    f"Code review failed for "
                    f"{segment.function_name}: {e}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

        # ── Step 4: Count valid tests ─────────────────────────────────────
        valid_count = sum(
            1 for t in validated_tests if t.is_syntactically_valid
        )

        logger.info(
            f"Pipeline complete | "
            f"valid_tests={valid_count}/{len(pipeline_input.segments)} | "
            f"reviews={len(code_review_reports)}"
        )

        return PipelineOutput(
            run_id=pipeline_input.run_id,
            repository_path=pipeline_input.repository_path,
            segments_processed=len(pipeline_input.segments),
            segments_with_valid_tests=valid_count,
            validated_tests=validated_tests,
            code_review_reports=code_review_reports,
            errors=errors,
        )