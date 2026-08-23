import os

from src.parser.ast_parser import parse_python_file
from src.extractor.feature_extractor import FeatureExtractor
from src.extractor.dependency_extractor import DependencyExtractor
from src.metrics.complexity_calculator import ComplexityCalculator
from src.metrics.nesting_depth_calculator import NestingDepthCalculator
from src.metrics.function_complexity_calculator import FunctionComplexityCalculator
from src.risk.risk_detector import RiskDetector
from src.output.json_formatter import format_as_json, save_json_to_file
from src.intelligence.testing_context_generator import TestingContextGenerator

# New imports for requirement-aware static analysis (extension)
from src.adapter.function_info_adapter import FunctionInfoAdapter
from src.requirement_analysis.parsers.parser_factory import RequirementParserFactory
from src.requirement_analysis.composite_extractor import CompositeRequirementExtractor
from src.integration.feature_matrix_builder import FeatureMatrixBuilder
from src.ingestion.github_fetcher import GitHubFetcher, GitHubFetchError


# Analyze one Python file and return all extracted metrics,
# risk details, and intelligent testing recommendations.
def analyze_file(file_path):

    # Parse source file into AST tree and raw source code
    tree, source_code = parse_python_file(file_path)

    # If parsing fails, skip this file
    if tree is None:
        return None

    # Extract basic structural features:
    # functions, if-count, loop-counts, total lines
    extractor = FeatureExtractor()
    extracted_features = extractor.extract(tree, source_code)

    # Calculate file-level cyclomatic complexity
    complexity_calculator = ComplexityCalculator()
    complexity = complexity_calculator.calculate(tree)

    # Calculate maximum nesting depth
    nesting_calculator = NestingDepthCalculator()
    nesting_depth = nesting_calculator.calculate(tree)

    # Extract function dependency relationships
    dependency_extractor = DependencyExtractor()
    dependencies = dependency_extractor.extract(tree)

    # Calculate cyclomatic complexity for each function
    function_complexity_calculator = FunctionComplexityCalculator()
    function_complexities = function_complexity_calculator.extract(tree)

    # Detect function risk levels using complexity and dependency count
    risk_detector = RiskDetector(function_complexities, dependencies)
    risk_results = risk_detector.detect_risk()

    # Get only high-risk function names
    high_risk_functions = [
        func for func, data in risk_results.items()
        if data["risk_level"] == "High"
    ]

    # Count number of high, medium, and low-risk functions
    risk_summary = {
        "high": sum(
            1 for item in risk_results.values()
            if item["risk_level"] == "High"
        ),
        "medium": sum(
            1 for item in risk_results.values()
            if item["risk_level"] == "Medium"
        ),
        "low": sum(
            1 for item in risk_results.values()
            if item["risk_level"] == "Low"
        )
    }

    # Generate ML-ready features and LLM-ready testing recommendations
    # This is the intelligence/novelty layer of the component
    testing_context_generator = TestingContextGenerator(
        function_complexities,
        dependencies,
        risk_results
    )

    intelligent_testing_context = testing_context_generator.generate()

    # Final structured output for frontend, API, MongoDB, and JSON files
    return {
        "file": file_path,

        # Overall file-level summary
        "summary": {
            "total_lines": extracted_features["total_lines"],
            "file_cyclomatic_complexity": complexity,
            "nesting_depth": nesting_depth,
            "total_dependency_calls": sum(
                len(dep_list) for dep_list in dependencies.values()
            )
        },

        # Control flow metrics
        "control_flow": {
            "if_count": extracted_features["if_count"],
            "for_count": extracted_features["for_count"],
            "while_count": extracted_features["while_count"]
        },

        # Function-level details
        "functions": {
            "total_functions": len(extracted_features["functions"]),
            "function_names": extracted_features["functions"],
            "function_complexity": function_complexities
        },

        # Function dependency mapping
        "dependencies": {
            "function_dependencies": dependencies
        },

        # Risk analysis output
        "risk_summary": risk_summary,
        "risk_analysis": risk_results,
        "high_risk_functions": high_risk_functions,

        # ML-ready + LLM-ready intelligent output
        "intelligent_testing_context": intelligent_testing_context
    }


# Analyze one Python file against requirements AUTO-EXTRACTED from its
# own docstrings -- no separate requirement file needed at all.
#
# This exists specifically for real, third-party code (e.g. a cloned
# open-source repository) where no hand-written TXT/JSON requirement
# document exists. If a function's docstring follows the Google-style
# Args/Returns/Raises convention, that docstring IS treated as its
# specification.
def analyze_file_with_auto_requirements(file_path):

    base_result = analyze_file(file_path)

    if base_result is None:
        return None

    tree, _source_code = parse_python_file(file_path)

    function_complexity_calculator = FunctionComplexityCalculator()
    function_complexities = function_complexity_calculator.extract(tree)

    dependency_extractor = DependencyExtractor()
    dependencies = dependency_extractor.extract(tree)

    function_infos = FunctionInfoAdapter().build(
        tree, function_complexities, dependencies
    )

    risk_detector = RiskDetector(function_complexities, dependencies)
    risk_results = risk_detector.detect_risk()

    # The only difference from analyze_file_with_requirements(): requirements
    # are auto-extracted from the code itself (docstrings first, type
    # hints as a fallback), not read from an external file.
    requirements = CompositeRequirementExtractor().extract(tree)

    requirement_analysis_output = FeatureMatrixBuilder().build(
        function_infos, requirements, risk_results
    )

    base_result["requirement_analysis"] = requirement_analysis_output

    return base_result


# Analyze one Python file AND compare it against a requirement document.
#
# This is the requirement-aware extension of analyze_file(). It does not
# modify analyze_file() at all -- it calls it as-is, then separately
# builds the requirement-to-code mapping, specification gap analysis,
# and unified feature matrix, and merges both results together.
def analyze_file_with_requirements(file_path, requirement_path):

    # Run the existing AST-based analysis exactly as before, untouched.
    base_result = analyze_file(file_path)

    if base_result is None:
        return None

    # Re-parse the file for the requirement-analysis pipeline. Re-parsing
    # here (rather than reusing internals from analyze_file) keeps this
    # function fully decoupled from analyze_file's implementation, so a
    # future change to either one can't silently break the other.
    tree, _source_code = parse_python_file(file_path)

    # Reuse the same calculators analyze_file() already uses.
    function_complexity_calculator = FunctionComplexityCalculator()
    function_complexities = function_complexity_calculator.extract(tree)

    dependency_extractor = DependencyExtractor()
    dependencies = dependency_extractor.extract(tree)

    # Build FunctionInfo objects (function name + real AST node + metrics)
    # that the requirement-analysis layer depends on.
    function_infos = FunctionInfoAdapter().build(
        tree, function_complexities, dependencies
    )

    # Reuse the existing risk detector, unchanged.
    risk_detector = RiskDetector(function_complexities, dependencies)
    risk_results = risk_detector.detect_risk()

    # Parse the requirement document (TXT or JSON, auto-detected).
    try:
        requirement_parser = RequirementParserFactory.get_parser(requirement_path)
        requirements = requirement_parser.parse(requirement_path)
    except ValueError as error:
        return {
            "file": file_path,
            "error": f"Failed to parse requirement document: {error}"
        }

    # Build the unified feature matrix: AST metrics + risk + spec metrics
    # + gap analysis, merged per function.
    requirement_analysis_output = FeatureMatrixBuilder().build(
        function_infos, requirements, risk_results
    )

    # Merge: everything analyze_file() already returns, plus the new
    # requirement-aware layer alongside it.
    base_result["requirement_analysis"] = requirement_analysis_output

    return base_result


# Analyze all Python files inside a folder/repository.
def analyze_folder(folder_path):

    results = []

    # Ignore unnecessary folders to avoid noisy analysis results
    ignored_folders = {
        "__pycache__",
        ".git",
        "venv",
        "migrations",
        "tests"
    }

    # Walk through folder and subfolders
    for root, dirs, files in os.walk(folder_path):

        # Remove ignored folders from traversal
        dirs[:] = [d for d in dirs if d not in ignored_folders]

        # Analyze only Python files
        for file in files:

            # Skip __init__.py and analyze normal .py files
            if file.endswith(".py") and not file.startswith("__"):

                full_path = os.path.join(root, file)

                # Analyze each Python file
                result = analyze_file(full_path)

                # Add valid analysis result to final list
                if result:
                    results.append(result)

    return results


# Analyze all Python files inside a folder, using requirements
# auto-extracted from each file's own docstrings/type hints -- the
# folder-level counterpart to analyze_file_with_auto_requirements().
#
# Mirrors analyze_folder()'s traversal logic exactly, without modifying
# analyze_folder() itself.
def analyze_folder_with_auto_requirements(folder_path):

    results = []

    ignored_folders = {
        "__pycache__",
        ".git",
        "venv",
        "migrations",
        "tests"
    }

    for root, dirs, files in os.walk(folder_path):

        dirs[:] = [d for d in dirs if d not in ignored_folders]

        for file in files:

            if file.endswith(".py") and not file.startswith("__"):

                full_path = os.path.join(root, file)

                result = analyze_file_with_auto_requirements(full_path)

                if result:
                    results.append(result)

    return results


# Aggregates per-file requirement_analysis summaries into one
# repo-level summary, weighted by function count per file.
def _build_repo_summary(file_results):

    total_functions = 0
    documented_and_implemented = 0
    documented_but_missing = 0
    implemented_but_undocumented = 0
    weighted_coverage_sum = 0.0

    for file_result in file_results:
        requirement_analysis = file_result.get("requirement_analysis")
        if not requirement_analysis:
            continue

        summary = requirement_analysis["project_summary"]
        total_functions += summary["total_functions"]
        documented_and_implemented += summary["documented_and_implemented"]
        documented_but_missing += summary["documented_but_missing"]
        implemented_but_undocumented += summary["implemented_but_undocumented"]
        weighted_coverage_sum += (
            summary["average_specification_coverage"] * summary["total_functions"]
        )

    overall_average_coverage = (
        round(weighted_coverage_sum / total_functions, 4) if total_functions else 0.0
    )

    return {
        "total_files_analyzed": len(file_results),
        "total_functions": total_functions,
        "documented_and_implemented": documented_and_implemented,
        "documented_but_missing": documented_but_missing,
        "implemented_but_undocumented": implemented_but_undocumented,
        "overall_average_specification_coverage": overall_average_coverage
    }


# Top-level entry point: clones a GitHub repository (or reuses an
# existing clone) and runs requirement-aware analysis across every
# Python file in it. This is the function the new
# /analyze-github-repo route calls.
def analyze_github_repository(repo_url, force_reclone=False):

    try:
        local_path = GitHubFetcher().clone(repo_url, force_reclone=force_reclone)
    except GitHubFetchError as error:
        return {"error": str(error)}

    file_results = analyze_folder_with_auto_requirements(local_path)

    return {
        "repo_url": repo_url,
        "local_path": local_path,
        "repo_summary": _build_repo_summary(file_results),
        "files": file_results
    }


# Runs only when this file is executed directly
if __name__ == "__main__":

    # Analyze sample dataset folder
    folder_results = analyze_folder("datasets")

    # Print formatted JSON output in terminal
    print(format_as_json(folder_results))

    # Save analysis result into JSON file
    save_json_to_file(
        folder_results,
        "results/analysis_results.json"
    )

    print("Analysis complete. Results saved to results/analysis_results.json")