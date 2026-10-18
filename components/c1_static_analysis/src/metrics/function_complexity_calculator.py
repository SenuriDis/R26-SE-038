
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

        # Each for loop adds a new execution path
        self.complexity += 1
        self.generic_visit(node)

    # Counts asynchronous for loops
    def visit_AsyncFor(self, node):

        # Async for loops also introduce a decision path
        self.complexity += 1
        self.generic_visit(node)

    # Counts while loops inside a function
    def visit_While(self, node):

        # Each while loop increases complexity
        self.complexity += 1
        self.generic_visit(node)

    # Counts boolean conditions such as AND / OR
    def visit_BoolOp(self, node):

        # Multiple conditions increase decision paths
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    # Counts conditional expressions such as:
    # result = value_if_true if condition else value_if_false
    def visit_IfExp(self, node):

        self.complexity += 1
        self.generic_visit(node)

    # Counts exception handlers as additional decision paths
    def visit_ExceptHandler(self, node):

        self.complexity += 1
        self.generic_visit(node)

    # Counts assert statements as decision checks
    def visit_Assert(self, node):

        self.complexity += 1
        self.generic_visit(node)

    # Do not include nested function complexity
    # in the enclosing function's complexity.
    def visit_FunctionDef(self, node):
        return

    def visit_AsyncFunctionDef(self, node):
        return

    # Calculate the current function's body without visiting
    # the function definition itself.
    def calculate(self, node):

        for statement in node.body:
            self.visit(statement)

        return self.complexity


# FunctionComplexityCalculator extracts complexity values
# for all functions in a Python file.
class FunctionComplexityCalculator(ast.NodeVisitor):

    def __init__(self):

        # Stores each function name with its complexity value
        self.function_complexities = {}

    # Visits each function definition in the AST
    def visit_FunctionDef(self, node):

        # Create a separate visitor for the current function
        visitor = SingleFunctionComplexityVisitor()

        # Calculate complexity using only this function's body
        self.function_complexities[node.name] = visitor.calculate(node)

        # Continue traversing to find nested and other functions
        self.generic_visit(node)

    # Supports asynchronous function definitions
    def visit_AsyncFunctionDef(self, node):

        visitor = SingleFunctionComplexityVisitor()
        self.function_complexities[node.name] = visitor.calculate(node)

        # Continue traversing to find nested and other functions
        self.generic_visit(node)

    # Main extraction method
    def extract(self, tree):

        # Reset results so repeated calls do not retain old values
        self.function_complexities = {}

        # Traverse the AST tree
        self.visit(tree)

        # Return all function-level complexity results
        return self.function_complexities
