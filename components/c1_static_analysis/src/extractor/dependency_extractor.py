
import ast


# DependencyExtractor analyzes function call relationships
# using Python AST (Abstract Syntax Tree)
class DependencyExtractor(ast.NodeVisitor):

    def __init__(self):

        # Stores dependencies for each function
        self.function_dependencies = {}

        # Tracks the function currently being visited
        self.current_function = None

    # Visits every function definition
    def visit_FunctionDef(self, node):

        self._visit_function(node)

    # Supports asynchronous function definitions
    def visit_AsyncFunctionDef(self, node):

        self._visit_function(node)

    # Handles function traversal while preserving the parent function
    def _visit_function(self, node):

        # Save the previous function context
        previous_function = self.current_function

        # Set current function
        self.current_function = node.name

        # Initialize dependency list without overwriting existing entries
        self.function_dependencies.setdefault(node.name, [])

        try:

            # Visit only this function's body
            for statement in node.body:
                self.visit(statement)

        finally:

            # Restore the previous function context
            self.current_function = previous_function

    # Visits every function call
    def visit_Call(self, node):

        # Only track calls inside functions
        if self.current_function is not None:

            # Extract called function name
            function_name = self._get_called_function_name(node)

            # Add dependency only if it has not been recorded
            if function_name:
                dependencies = self.function_dependencies[
                    self.current_function
                ]

                if function_name not in dependencies:
                    dependencies.append(function_name)

        # Continue traversing AST nodes
        self.generic_visit(node)

    # Helper method to identify called function names
    def _get_called_function_name(self, node):

        # Example: login()
        if isinstance(node.func, ast.Name):
            return node.func.id

        # Example: user.login()
        if isinstance(node.func, ast.Attribute):
            return node.func.attr

        return None

    # Main extraction method
    def extract(self, tree):

        # Reset results before each extraction
        self.function_dependencies = {}
        self.current_function = None

        # Traverse AST tree
        self.visit(tree)

        # Return dependency mapping
        return self.function_dependencies
