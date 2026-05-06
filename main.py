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


def analyze_file(file_path):
    tree, source_code = parse_python_file(file_path)

    if tree is None:
        return None

    extractor = FeatureExtractor()
    extracted_features = extractor.extract(tree, source_code)

    complexity_calculator = ComplexityCalculator()
    complexity = complexity_calculator.calculate(tree)

    nesting_calculator = NestingDepthCalculator()
    nesting_depth = nesting_calculator.calculate(tree)

    dependency_extractor = DependencyExtractor()
    dependencies = dependency_extractor.extract(tree)

    function_complexity_calculator = FunctionComplexityCalculator()
    function_complexities = function_complexity_calculator.extract(tree)

    risk_detector = RiskDetector(function_complexities, dependencies)
    risk_results = risk_detector.detect_risk()

    high_risk_functions = [
        func for func, data in risk_results.items()
        if data["risk_level"] == "High"
    ]

    risk_summary = {
        "high": sum(1 for item in risk_results.values() if item["risk_level"] == "High"),
        "medium": sum(1 for item in risk_results.values() if item["risk_level"] == "Medium"),
        "low": sum(1 for item in risk_results.values() if item["risk_level"] == "Low")
    }

    testing_context_generator = TestingContextGenerator(
    function_complexities,
    dependencies,
    risk_results
)

    intelligent_testing_context = testing_context_generator.generate()

    return {
        "file": file_path,
        "summary": {
            "total_lines": extracted_features["total_lines"],
            "file_cyclomatic_complexity": complexity,
            "nesting_depth": nesting_depth,
            "total_dependency_calls": sum(len(dep_list) for dep_list in dependencies.values())
        },
        "control_flow": {
            "if_count": extracted_features["if_count"],
            "for_count": extracted_features["for_count"],
            "while_count": extracted_features["while_count"]
        },
        "functions": {
            "total_functions": len(extracted_features["functions"]),
            "function_names": extracted_features["functions"],
            "function_complexity": function_complexities
        },
        "dependencies": {
            "function_dependencies": dependencies
        },
        "risk_summary": risk_summary,
        "risk_analysis": risk_results,
        "high_risk_functions": high_risk_functions,
        "intelligent_testing_context": intelligent_testing_context
        
    }


def analyze_folder(folder_path):
    results = []
    ignored_folders = {"__pycache__", ".git", "venv", "migrations", "tests"}

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in ignored_folders]

        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                full_path = os.path.join(root, file)

                result = analyze_file(full_path)
                if result:
                    results.append(result)

    return results


if __name__ == "__main__":
    folder_results = analyze_folder("datasets")

    print(format_as_json(folder_results))

    save_json_to_file(folder_results, "results/analysis_results.json")
    print("Analysis complete. Results saved to results/analysis_results.json")