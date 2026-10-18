
import ast


# ComplexityCalculator calculates cyclomatic complexity
# using Python AST (Abstract Syntax Tree).
#
# Cyclomatic Complexity measures how many independent
# execution paths exist in the source code.
class ComplexityCalculator(ast.NodeVisitor):

    def __init__(self):

        # Base complexity starts at 1
        # Even a simple function has one execution path
        self.complexity = 1

    # Visits every if statement
    def visit_If(self, node):

        # Each conditional branch increases complexity
        self.complexity += 1

        # Continue traversing nested nodes
        self.generic_visit(node)

    # Visits every for loop
    def visit_For(self, node):

        # Loops introduce additional execution paths
        self.complexity += 1
        self.generic_visit(node)

    # Visits asynchronous for loops
    def visit_AsyncFor(self, node):

        # Async loops also introduce execution paths
        self.complexity += 1
        self.generic_visit(node)

    # Visits every while loop
    def visit_While(self, node):

        # While loops also increase complexity
        self.complexity += 1
        self.generic_visit(node)

    # Visits boolean operations such as:
    # if a and b or c
    def visit_BoolOp(self, node):

        # Multiple boolean conditions increase complexity
        # Example:
        # a and b and c = +2 complexity
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    # Visits conditional expressions such as:
    # result = value1 if condition else value2
    def visit_IfExp(self, node):

        # A conditional expression adds a decision path
        self.complexity += 1
        self.generic_visit(node)

    # Visits exception handlers
    def visit_ExceptHandler(self, node):

        # An exception handler adds a decision path
        self.complexity += 1
        self.generic_visit(node)

    # Main method used to calculate complexity
    def calculate(self, tree):

        # Reset complexity before each calculation
        self.complexity = 1

        # Traverse AST tree
        self.visit(tree)

        # Return final cyclomatic complexity score
        return self.complexity
