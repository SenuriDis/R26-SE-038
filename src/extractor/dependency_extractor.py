import ast


class DependencyExtractor(ast.NodeVisitor):
    def __init__(self):
        self.function_dependencies = {}
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.function_dependencies[self.current_function] = []
        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node):
        if self.current_function is not None:
            function_name = self._get_called_function_name(node)
            if function_name:
                self.function_dependencies[self.current_function].append(function_name)

        self.generic_visit(node)

    def _get_called_function_name(self, node):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def extract(self, tree):
        self.visit(tree)

        for function_name in self.function_dependencies:
            self.function_dependencies[function_name] = list(set(self.function_dependencies[function_name]))

        return self.function_dependencies