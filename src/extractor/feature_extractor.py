import ast


class FeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.if_count = 0
        self.for_count = 0
        self.while_count = 0
        self.total_lines = 0

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_If(self, node):
        self.if_count += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.for_count += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.while_count += 1
        self.generic_visit(node)

    def extract(self, tree, source_code=None):
        self.visit(tree)

        if source_code is not None:
            self.total_lines = len(source_code.splitlines())

        return {
            "functions": list(dict.fromkeys(self.functions)),
            "if_count": self.if_count,
            "for_count": self.for_count,
            "while_count": self.while_count,
            "total_lines": self.total_lines
        }