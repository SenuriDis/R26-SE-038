import ast


# SingleFunctionComplexityVisitor calculates cyclomatic complexity
# for ONE function at a time.
class SingleFunctionComplexityVisitor(ast.NodeVisitor):

    def __init__(self):

        # Base complexity starts at 1
        # A function always has at least one execution path
        self.complexity = 1

    # Counts if statements inside a function
    def visit_If(self, node):

        # Each if condition adds a new decision path
        self.complexity += 1

        # Continue checking nested code
        self.generic_visit(node)

    # Counts for loops inside a function
    def visit_For(self, node):

        # Each for loop adds a possible execution path
        self.complexity += 1

        # Continue checking nested code
        self.generic_visit(node)

    # Counts while loops inside a function
    def visit_While(self, node):

        # Each while loop increases complexity
        self.complexity += 1

        # Continue checking nested code
        self.generic_visit(node)

    # Counts boolean conditions such as AND / OR
    def visit_BoolOp(self, node):

        # Multiple conditions increase decision paths
        self.complexity += len(node.values) - 1

        # Continue checking nested code
        self.generic_visit(node)


# FunctionComplexityCalculator extracts complexity values
# for all functions in a Python file.
class FunctionComplexityCalculator(ast.NodeVisitor):

    def __init__(self):

        # Stores each function name with its complexity value
        # Example:
        # {
        #   "login": 3,
        #   "validate_user": 1
        # }
        self.function_complexities = {}

    # Visits each function definition in the AST
    def visit_FunctionDef(self, node):

        # Create a separate visitor for the current function
        visitor = SingleFunctionComplexityVisitor()

        # Calculate complexity only for this function
        visitor.visit(node)

        # Store calculated complexity using function name
        self.function_complexities[node.name] = visitor.complexity

        # Continue traversing remaining functions/nodes
        self.generic_visit(node)

    # Main extraction method
    def extract(self, tree):

        # Traverse the AST tree
        self.visit(tree)

        # Return all function-level complexity results
        return self.function_complexities