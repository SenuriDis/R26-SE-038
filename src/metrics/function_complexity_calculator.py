import ast


class SingleFunctionComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


class FunctionComplexityCalculator(ast.NodeVisitor):
    def __init__(self):
        self.function_complexities = {}

    def visit_FunctionDef(self, node):
        visitor = SingleFunctionComplexityVisitor()
        visitor.visit(node)
        self.function_complexities[node.name] = visitor.complexity
        self.generic_visit(node)

    def extract(self, tree):
        self.visit(tree)
        return self.function_complexities