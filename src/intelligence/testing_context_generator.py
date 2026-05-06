class TestingContextGenerator:
    def __init__(self, function_complexities, function_dependencies, risk_results):
        self.function_complexities = function_complexities
        self.function_dependencies = function_dependencies
        self.risk_results = risk_results

    def generate(self):
        ml_ready_features = []
        llm_test_recommendations = []

        for function_name, risk_data in self.risk_results.items():
            complexity = risk_data["complexity"]
            dependency_count = risk_data["dependency_count"]
            risk_level = risk_data["risk_level"]
            dependencies = self.function_dependencies.get(function_name, [])

            ml_ready_features.append({
                "function_name": function_name,
                "cyclomatic_complexity": complexity,
                "dependency_count": dependency_count,
                "risk_level": risk_level
            })

            suggested_focus = self._get_test_focus(complexity, dependency_count, risk_level)

            llm_test_recommendations.append({
                "function": function_name,
                "risk_level": risk_level,
                "reason": self._generate_reason(complexity, dependency_count, risk_level),
                "dependencies": dependencies,
                "suggested_test_focus": suggested_focus
            })

        return {
            "ml_ready_features": ml_ready_features,
            "llm_test_recommendations": llm_test_recommendations
        }

    def _generate_reason(self, complexity, dependency_count, risk_level):
        reasons = []

        if complexity >= 4:
            reasons.append("high cyclomatic complexity")
        elif complexity == 3:
            reasons.append("moderate cyclomatic complexity")

        if dependency_count >= 3:
            reasons.append("high dependency count")
        elif dependency_count == 2:
            reasons.append("moderate dependency count")

        if not reasons:
            reasons.append("low structural complexity")

        return f"{risk_level} risk due to " + " and ".join(reasons)

    def _get_test_focus(self, complexity, dependency_count, risk_level):
        focus = []

        if complexity >= 3:
            focus.extend([
                "branch coverage",
                "edge cases",
                "multiple execution paths"
            ])

        if dependency_count >= 2:
            focus.extend([
                "dependency behavior",
                "mocking external/internal calls",
                "integration-related scenarios"
            ])

        if risk_level == "Low":
            focus.append("basic functional correctness")

        return list(dict.fromkeys(focus))