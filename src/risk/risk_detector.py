class RiskDetector:
    def __init__(self, function_complexities, function_dependencies):
        self.function_complexities = function_complexities
        self.function_dependencies = function_dependencies

    def detect_risk(self):
        risk_results = {}

        for function_name, complexity in self.function_complexities.items():
            dependencies = self.function_dependencies.get(function_name, [])
            dependency_count = len(dependencies)

            if complexity >= 4 or dependency_count >= 3:
                risk_level = "High"
            elif complexity == 3 or dependency_count == 2:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            risk_results[function_name] = {
                "complexity": complexity,
                "dependency_count": dependency_count,
                "risk_level": risk_level
            }

        return risk_results