import ast


# DependencyExtractor analyzes function call relationships
# using Python AST (Abstract Syntax Tree)
class DependencyExtractor(ast.NodeVisitor):

    def __init__(self):

        # Stores dependencies for each function
        self.function_dependencies = {}

        # Tracks the function currently being visited
        self.current_function = None

    # Visits every function definition in the Python source code
    def visit_FunctionDef(self, node):

        # Store current function name
        self.current_function = node.name

        # Initialize empty dependency list for the function
        self.function_dependencies[self.current_function] = []

        # Continue traversing inside the function body
        self.generic_visit(node)

        # Reset after finishing function traversal
        self.current_function = None

    # Visits every function call inside the source code
    def visit_Call(self, node):

        # Only track calls inside functions
        if self.current_function is not None:

            # Extract called function name
            function_name = self._get_called_function_name(node)

            # Add dependency if valid function name exists
            if function_name:
                self.function_dependencies[self.current_function].append(
                    function_name
                )

        # Continue traversing AST nodes
        self.generic_visit(node)

    # Helper method to identify called function names
    def _get_called_function_name(self, node):

        # Example:
        # login()
        if isinstance(node.func, ast.Name):
            return node.func.id

        # Example:
        # user.login()
        if isinstance(node.func, ast.Attribute):
            return node.func.attr

        return None

    # Main extraction method
    def extract(self, tree):

        # Traverse AST tree
        self.visit(tree)

        # Remove duplicate dependencies
        for function_name in self.function_dependencies:
            self.function_dependencies[function_name] = list(
                set(self.function_dependencies[function_name])
            )

        # Return dependency mapping
        return self.function_dependencies