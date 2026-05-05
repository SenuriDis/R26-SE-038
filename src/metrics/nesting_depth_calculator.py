import ast


class NestingDepthCalculator(ast.NodeVisitor):
    def __init__(self):
        self.current_depth = 0
        self.max_depth = 0

    def _enter_block(self):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)

    def _exit_block(self):
        self.current_depth -= 1

    def visit_If(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_For(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_While(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def calculate(self, tree):
        self.visit(tree)
        return self.max_depth