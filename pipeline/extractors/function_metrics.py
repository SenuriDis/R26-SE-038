"""
Derives the eight C2 metrics that C1 measures internally but never writes out.

C1's FunctionInfoAdapter already keeps the live ast.FunctionDef node on every
FunctionInfo it builds, so none of this needs a re-parse -- we just walk a node
C1 is already holding.

Scoping note: every count here stops at a nested function boundary. A `for`
loop inside a closure belongs to the closure, not to the function that defines
it. C1's own FunctionInfoAdapter emits a separate FunctionInfo for each nested
function, so counting the nested body in both places would double-count it.
"""

import ast
from typing import Dict, Union

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]

_LOOP_NODES = (ast.For, ast.AsyncFor, ast.While)
_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _walk_own_body(node: FunctionNode):
    """
    Yield every descendant of `node` that belongs to this function specifically,
    descending into control flow but never into a nested function or class.
    """
    stack = list(ast.iter_child_nodes(node))

    while stack:
        current = stack.pop()
        yield current

        # A nested function or class owns its own body -- it gets its own
        # FunctionInfo from C1, so we stop here rather than counting twice.
        if isinstance(current, _FUNCTION_NODES + (ast.ClassDef,)):
            continue

        stack.extend(ast.iter_child_nodes(current))


def count_parameters(node: FunctionNode) -> int:
    """Every parameter the function accepts, including *args and **kwargs."""
    args = node.args
    total = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
    if args.vararg is not None:
        total += 1
    if args.kwarg is not None:
        total += 1
    return total


def has_recursion(node: FunctionNode) -> bool:
    """
    True when the function calls itself by name.

    Catches both a direct `foo()` and an attribute call `self.foo()`. It will
    not catch indirect recursion through another function, which would need a
    call graph -- the same thing fan_in is waiting on.
    """
    own_name = node.name

    for child in _walk_own_body(node):
        if not isinstance(child, ast.Call):
            continue

        func = child.func
        if isinstance(func, ast.Name) and func.id == own_name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == own_name:
            return True

    return False


def extract(node: FunctionNode) -> Dict[str, object]:
    """
    Return the eight fields C2 wants that C1 does not currently write out.

    Field names match FunctionMetricsRequest exactly, so the result can be
    splatted straight into the C2 request payload.
    """
    end_line = getattr(node, "end_lineno", None)

    num_loops = 0
    num_conditionals = 0
    num_returns = 0
    num_handlers = 0

    for child in _walk_own_body(node):
        if isinstance(child, _LOOP_NODES):
            num_loops += 1
        elif isinstance(child, ast.If):
            num_conditionals += 1
        elif isinstance(child, ast.Return):
            num_returns += 1
        elif isinstance(child, ast.ExceptHandler):
            num_handlers += 1

    return {
        "start_line": node.lineno,
        # Fall back to the start line when end_lineno is unavailable, so the
        # span stays a valid 1-line range rather than becoming 0.
        "end_line": end_line if end_line is not None else node.lineno,
        "num_parameters": count_parameters(node),
        "num_return_statements": num_returns,
        "num_exception_handlers": num_handlers,
        "num_loops": num_loops,
        "num_conditionals": num_conditionals,
        "has_recursion": has_recursion(node),
    }
