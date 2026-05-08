# RiskDetector identifies the structural risk level
# of each function based on:
# - Cyclomatic complexity
# - Dependency count
#
# This helps prioritize software testing efforts.
class RiskDetector:

    def __init__(self, function_complexities, function_dependencies):

        # Stores function-level cyclomatic complexity values
        # Example:
        # {"login": 4, "validate_user": 2}
        self.function_complexities = function_complexities

        # Stores dependency relationships between functions
        # Example:
        # {"login": ["validate_user", "connect_db"]}
        self.function_dependencies = function_dependencies

    # Main method used to classify function risk levels
    def detect_risk(self):

        # Stores final risk analysis results
        risk_results = {}

        # Analyze each function individually
        for function_name, complexity in self.function_complexities.items():

            # Get dependency list for the current function
            dependencies = self.function_dependencies.get(function_name, [])

            # Count number of dependencies
            dependency_count = len(dependencies)

            # Risk classification logic

            # High Risk:
            # Very complex OR heavily dependent functions
            if complexity >= 4 or dependency_count >= 3:
                risk_level = "High"

            # Medium Risk:
            # Moderately complex OR moderately dependent functions
            elif complexity == 3 or dependency_count == 2:
                risk_level = "Medium"

            # Low Risk:
            # Simple functions with fewer dependencies
            else:
                risk_level = "Low"

            # Store analyzed risk details
            risk_results[function_name] = {
                "complexity": complexity,
                "dependency_count": dependency_count,
                "risk_level": risk_level
            }

        # Return final risk analysis results
        return risk_results