
import logging
from src.models.schemas import (
    PipelineInput,
    PipelineOutput,
)
from src.rag.indexer import RepositoryIndexer
from src.rag.retriever import RepositoryRetriever
from src.agents.agent1_test_generation import Agent1TestGeneration
from src.agents.agent2_test_validation import Agent2TestValidation
from src.agents.agent3_code_review import Agent3CodeReview

logger = logging.getLogger(__name__)


class TestingPipeline:
    def __init__(self, force_reindex: bool = False):
        self.force_reindex = force_reindex
        logger.info("TestingPipeline initialised")

    def run(self, pipeline_input: PipelineInput) -> PipelineOutput:
        logger.info(
            f"Pipeline starting | run_id={pipeline_input.run_id} | "
            f"segments={len(pipeline_input.segments)}"
        )

        validated_tests = []
        code_review_reports = []
        errors = []

        # ── Phase 1: RAG Index ─────────────────────────────────────────────
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

        # ── Phase 2: Initialise Agents ─────────────────────────────────────
        agent1 = Agent1TestGeneration(retriever)
        agent2 = Agent2TestValidation(retriever)
        agent3 = Agent3CodeReview(retriever)

        # ── Phase 3: Process Each Segment ─────────────────────────────────
        for i, segment in enumerate(pipeline_input.segments):
            logger.info(
                f"Processing segment {i+1}/{len(pipeline_input.segments)} "
                f"| function={segment.function_name}"
            )

            # Path A: Agent 1 → Agent 2
            try:
                # Agent 1 generates test cases + test code
                raw_output = agent1.run(segment)

                # Agent 2 validates traceability + AST + dry run
                validated = agent2.run(
                    raw_output,
                    segment.source_code,
                    repo_path=pipeline_input.repository_path,
                )
                validated_tests.append(validated)

                # Log test case summary
                if raw_output.test_case_set:
                    logger.info(
                        f"Test cases generated: "
                        f"{raw_output.test_case_set.total_test_cases} | "
                        f"function={segment.function_name}"
                    )
                if validated.traceability_report:
                    logger.info(
                        f"Traceability: "
                        f"{validated.traceability_report.covered_count}/"
                        f"{validated.traceability_report.total_test_cases} "
                        f"covered | function={segment.function_name}"
                    )

            except Exception as e:
                error_msg = (
                    f"Test generation failed for "
                    f"{segment.function_name}: {e}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

            # Path B: Agent 3 (independent)
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

        # ── Phase 4: Collect Results ───────────────────────────────────────
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

    def run_from_ml_report(
        self,
        repository_path: str,
        enriched_segments: list,
        run_id: str,
    ) -> PipelineOutput:
        """
        Run the pipeline from Component 2's ML risk report.

        Unlike `run`, this consumes `EnrichedSegment` objects produced by
        `MLReportReader`, so the ML-guided signals (tier, test depth,
        minimum test cases, focus test types, risk explanation and top
        risk factors) are forwarded into Agent 1.

        Args:
            repository_path: Path to the repository under test
            enriched_segments: List of EnrichedSegment from MLReportReader
            run_id: Identifier for this run

        Returns:
            PipelineOutput with all validated tests and review reports
        """
        logger.info(
            f"Pipeline starting from ML report | run_id={run_id} | "
            f"segments={len(enriched_segments)}"
        )

        validated_tests = []
        code_review_reports = []
        errors = []

        # ── Phase 1: RAG Index ─────────────────────────────────────────────
        try:
            logger.info("Building RAG index...")
            indexer = RepositoryIndexer(repository_path)
            index = indexer.build_index(force_rebuild=self.force_reindex)
            retriever = RepositoryRetriever(index)
            stats = indexer.get_stats()
            logger.info(f"RAG index ready | chunks={stats['total_chunks']}")
        except Exception as e:
            error_msg = f"RAG indexing failed: {e}"
            logger.error(error_msg)
            return PipelineOutput(
                run_id=run_id,
                repository_path=repository_path,
                segments_processed=0,
                segments_with_valid_tests=0,
                errors=[error_msg],
            )

        # ── Phase 2: Initialise Agents ─────────────────────────────────────
        agent1 = Agent1TestGeneration(retriever)
        agent2 = Agent2TestValidation(retriever)
        agent3 = Agent3CodeReview(retriever)

        # ── Phase 3: Process Each Enriched Segment ────────────────────────
        for i, enriched in enumerate(enriched_segments):
            segment = enriched.segment
            logger.info(
                f"Processing segment {i+1}/{len(enriched_segments)} "
                f"| function={segment.function_name} "
                f"| tier={enriched.risk_level}"
            )

            # Path A: Agent 1 (ML-guided) → Agent 2
            try:
                raw_output = agent1.run(
                    segment,
                    risk_level=enriched.risk_level,
                    test_depth=enriched.test_depth,
                    min_test_cases=enriched.min_test_cases,
                    test_types=enriched.test_types,
                    explanation_text=enriched.explanation_text,
                    top_risk_factors=enriched.top_risk_factors,
                )

                validated = agent2.run(
                    raw_output,
                    segment.source_code,
                    repo_path=repository_path,
                )
                validated_tests.append(validated)

                if raw_output.test_case_set:
                    logger.info(
                        f"Test cases generated: "
                        f"{raw_output.test_case_set.total_test_cases} | "
                        f"function={segment.function_name}"
                    )
                if validated.traceability_report:
                    logger.info(
                        f"Traceability: "
                        f"{validated.traceability_report.covered_count}/"
                        f"{validated.traceability_report.total_test_cases} "
                        f"covered | function={segment.function_name}"
                    )

            except Exception as e:
                error_msg = (
                    f"Test generation failed for "
                    f"{segment.function_name}: {e}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

            # Path B: Agent 3 (independent)
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

        # ── Phase 4: Collect Results ───────────────────────────────────────
        valid_count = sum(
            1 for t in validated_tests if t.is_syntactically_valid
        )

        logger.info(
            f"Pipeline complete | "
            f"valid_tests={valid_count}/{len(enriched_segments)} | "
            f"reviews={len(code_review_reports)}"
        )

        return PipelineOutput(
            run_id=run_id,
            repository_path=repository_path,
            segments_processed=len(enriched_segments),
            segments_with_valid_tests=valid_count,
            validated_tests=validated_tests,
            code_review_reports=code_review_reports,
            errors=errors,
        )