
import ast


# NestingDepthCalculator measures the maximum nesting depth
# of control structures in the source code.
#
# Example:
# if -> for -> while
# nesting depth = 3
class NestingDepthCalculator(ast.NodeVisitor):

    def __init__(self):

        # Tracks current nesting level while traversing AST
        self.current_depth = 0

        # Stores the highest nesting level detected
        self.max_depth = 0

    # Called when entering a nested block
    def _enter_block(self):

        # Increase current nesting level
        self.current_depth += 1

        # Update maximum depth if current depth is higher
        self.max_depth = max(self.max_depth, self.current_depth)

    # Called when exiting a nested block
    def _exit_block(self):

        # Decrease current nesting level
        self.current_depth -= 1

    # Helper method to safely visit a nested block
    def _visit_nested_block(self, node):

        self._enter_block()

        try:
            self.generic_visit(node)
        finally:
            self._exit_block()

    # Visits if statements
    def visit_If(self, node):
        self._visit_nested_block(node)

    # Visits for loops
    def visit_For(self, node):
        self._visit_nested_block(node)

    # Visits asynchronous for loops
    def visit_AsyncFor(self, node):
        self._visit_nested_block(node)

    # Visits while loops
    def visit_While(self, node):
        self._visit_nested_block(node)

    # Main method used to calculate maximum nesting depth
    def calculate(self, tree):

        # Reset values before each calculation
        self.current_depth = 0
        self.max_depth = 0

        # Traverse AST tree
        self.visit(tree)

        # Return maximum nesting depth detected
        return self.max_depth
