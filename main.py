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