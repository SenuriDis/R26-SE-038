
import ast


# FeatureExtractor extracts structural source code features
# using Python AST (Abstract Syntax Tree)
class FeatureExtractor(ast.NodeVisitor):

    def __init__(self):

        # Stores detected function names
        self.functions = []

        # Counts conditional statements
        self.if_count = 0

        # Counts for-loops
        self.for_count = 0

        # Counts while-loops
        self.while_count = 0

        # Stores total number of lines in source code
        self.total_lines = 0

    # Visits every function definition
    def visit_FunctionDef(self, node):

        self.functions.append(node.name)
        self.generic_visit(node)

    # Supports asynchronous function definitions
    def visit_AsyncFunctionDef(self, node):

        self.functions.append(node.name)
        self.generic_visit(node)

    # Visits every if statement
    def visit_If(self, node):

        self.if_count += 1
        self.generic_visit(node)

    # Visits every for loop
    def visit_For(self, node):

        self.for_count += 1
        self.generic_visit(node)

    # Visits asynchronous for loops
    def visit_AsyncFor(self, node):

        self.for_count += 1
        self.generic_visit(node)

    # Visits every while loop
    def visit_While(self, node):

        self.while_count += 1
        self.generic_visit(node)

    # Main feature extraction method
    def extract(self, tree, source_code=None):

        # Reset values before each extraction
        self.functions = []
        self.if_count = 0
        self.for_count = 0
        self.while_count = 0
        self.total_lines = 0

        # Traverse AST tree
        self.visit(tree)

        # Count total source code lines
        if source_code is not None:
            self.total_lines = len(source_code.splitlines())

        # Return extracted structural features
        return {

            # Remove duplicate function names
            "functions": list(dict.fromkeys(self.functions)),

            # Control flow metrics
            "if_count": self.if_count,
            "for_count": self.for_count,
            "while_count": self.while_count,

            # Source code size
            "total_lines": self.total_lines
        }
