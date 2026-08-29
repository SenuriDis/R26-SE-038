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

        # Decrease nesting level
        self.current_depth -= 1

    # Visits if statements
    def visit_If(self, node):

        # Enter nested if block
        self._enter_block()

        # Continue traversing nested code
        self.generic_visit(node)

        # Exit block after traversal
        self._exit_block()

    # Visits for loops
    def visit_For(self, node):

        # Enter nested for block
        self._enter_block()

        # Continue traversing nested code
        self.generic_visit(node)

        # Exit block after traversal
        self._exit_block()

    # Visits while loops
    def visit_While(self, node):

        # Enter nested while block
        self._enter_block()

        # Continue traversing nested code
        self.generic_visit(node)

        # Exit block after traversal
        self._exit_block()

    # Main method used to calculate maximum nesting depth
    def calculate(self, tree):

        # Traverse AST tree
        self.visit(tree)

        # Return maximum nesting depth detected
        return self.max_depth