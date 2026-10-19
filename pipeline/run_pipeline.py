#!/usr/bin/env python3
"""Run the C1 -> C2 -> C3 -> C4 pipeline through the component HTTP APIs."""

import argparse
import ast
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.extractors.function_metrics import extract as extract_function_metrics

C2_DEFAULTS = {
    "commit_frequency": 0,
    "author_count": 1,
    "bug_history": 0,
    "days_since_last_change": 999,
    "fan_in": 0,
}
CONTROL_FLOW_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
)
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
MAX_HANDOFF_BYTES = 20 * 1024 * 1024


class PipelineError(RuntimeError):
    """Raised when a component request or data handoff fails."""


def post_json(url: str, payload: Dict, timeout: int) -> Dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise PipelineError(f"{url} returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise PipelineError(f"Could not reach {url}: {error.reason}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PipelineError(f"{url} returned an invalid JSON response.") from error

    if not isinstance(result, dict) and not isinstance(result, list):
        raise PipelineError(f"{url} returned an unexpected JSON value.")
    return result


def _relative_analysis_path(file_name: str, container_target: str) -> str:
    target = PurePosixPath(container_target.replace("\\", "/"))
    analyzed_file = PurePosixPath(file_name.replace("\\", "/"))
    if analyzed_file.is_absolute():
        try:
            relative = analyzed_file.relative_to(target)
        except ValueError as error:
            raise PipelineError(
                f"C1 returned {file_name!r}, which is outside its target {container_target!r}."
            ) from error
    else:
        relative = analyzed_file
    if not relative.parts or ".." in relative.parts:
        raise PipelineError(f"C1 returned an unsafe file path: {file_name!r}.")
    return relative.as_posix()


def _find_functions(tree: ast.AST) -> Dict[str, List[ast.AST]]:
    functions: Dict[str, List[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_NODES):
            functions.setdefault(node.name, []).append(node)
    return functions


def _function_nesting_depth(function: ast.AST) -> int:
    maximum = 0
    stack: List[Tuple[ast.AST, int]] = [(function, 0)]
    while stack:
        node, depth = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (FUNCTION_NODES + (ast.ClassDef,))):
                continue
            child_depth = depth + int(isinstance(child, CONTROL_FLOW_NODES))
            maximum = max(maximum, child_depth)
            stack.append((child, child_depth))
    return maximum


def adapt_c1_response(
    response: object,
    local_target: Path,
    container_target: str,
    project_name: str,
) -> Tuple[Dict, Dict[str, str], Dict[str, ast.AST]]:
    """Convert C1's native folder report to the C2 request shape."""
    def resolve_source(file_name: str) -> Tuple[str, str]:
        relative_path = _relative_analysis_path(file_name, container_target)
        source_path = local_target / Path(*PurePosixPath(relative_path).parts)
        try:
            return relative_path, source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise PipelineError(f"Could not read source file {source_path}: {error}") from error

    return _adapt_c1_reports(response, project_name, resolve_source)


def adapt_c1_payload(
    response: object,
    source_files: Dict[str, str],
    project_name: str,
) -> Tuple[Dict, Dict[str, str], Dict[str, ast.AST]]:
    """Adapt C1 reports and source text supplied by the browser wizard."""
    normalized_sources = {
        PurePosixPath(name.replace("\\", "/")).as_posix(): contents
        for name, contents in source_files.items()
        if isinstance(name, str) and isinstance(contents, str)
    }

    def resolve_source(file_name: str) -> Tuple[str, str]:
        normalized_name = file_name.replace("\\", "/")
        path = PurePosixPath(normalized_name)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise PipelineError(f"C1 returned an unsafe source path: {file_name!r}.")
        relative_path = path.as_posix()
        source = normalized_sources.get(relative_path)
        if source is None:
            raise PipelineError(
                f"C1 source file {relative_path!r} was not included in the wizard handoff."
            )
        return relative_path, source

    return _adapt_c1_reports(response, project_name, resolve_source)


def _adapt_c1_reports(
    response: object,
    project_name: str,
    resolve_source,
) -> Tuple[Dict, Dict[str, str], Dict[str, ast.AST]]:
    if isinstance(response, dict):
        response = response.get("files", response.get("results"))
    if not isinstance(response, list):
        raise PipelineError("C1 response did not contain a list of file reports.")

    functions: List[Dict] = []
    source_by_path: Dict[str, str] = {}
    definitions_by_path: Dict[str, ast.AST] = {}

    for file_report in response:
        if not isinstance(file_report, dict) or not file_report.get("file"):
            continue
        file_name = str(file_report["file"])
        try:
            relative_path, source = resolve_source(file_name)
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as error:
            raise PipelineError(f"Could not parse C1 source file {file_name}: {error}") from error

        source_by_path[relative_path] = source
        file_functions = _find_functions(tree)
        function_data = file_report.get("functions", {})
        names = function_data.get("function_names", [])
        complexity = function_data.get("function_complexity", {})
        dependencies = file_report.get("dependencies", {}).get(
            "function_dependencies", {}
        )

        for name in names:
            candidates = file_functions.get(name, [])
            if not candidates:
                raise PipelineError(
                    f"C1 reported {name!r} in {relative_path}, but it was not found in that source."
                )
            for node in candidates:
                metrics = extract_function_metrics(node)
                lines_of_code = max(
                    1,
                    getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                )
                calls = dependencies.get(name, [])
                if not isinstance(calls, list):
                    calls = []
                functions.append({
                    "function_name": name,
                    "file_path": relative_path,
                    "start_line": metrics["start_line"],
                    "end_line": metrics["end_line"],
                    "cyclomatic_complexity": max(1, int(complexity.get(name, 1))),
                    "nesting_depth": _function_nesting_depth(node),
                    "lines_of_code": lines_of_code,
                    "fan_out": len(calls),
                    "dependencies": calls,
                    **C2_DEFAULTS,
                    **metrics,
                })
                definitions_by_path[f"{relative_path}:{metrics['start_line']}"] = node

    if not functions:
        raise PipelineError("C1 completed but returned no Python functions for C2.")
    return (
        {"project_name": project_name, "functions": functions},
        source_by_path,
        definitions_by_path,
    )


def _source_for_ranked_function(
    ranked: Dict,
    sources: Dict[str, str],
    definitions: Dict[str, ast.AST],
) -> str:
    file_path = str(ranked.get("file_path", ""))
    start_line = int(ranked.get("start_line", 1))
    node = definitions.get(f"{file_path}:{start_line}")
    if node is None:
        candidates = [
            definition
            for key, definition in definitions.items()
            if key.startswith(f"{file_path}:")
            and getattr(definition, "name", None) == ranked.get("function_name")
        ]
        if candidates:
            node = candidates[0]
    if node is None or file_path not in sources:
        raise PipelineError(
            f"Could not locate source for C2 function {ranked.get('function_name')!r} ({file_path})."
        )
    return ast.get_source_segment(sources[file_path], node) or ""


def _source_files(source_root: Path) -> Dict[str, str]:
    source_files: Dict[str, str] = {}
    ignored = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        ".pytest_cache", "tests", "test",
    }
    for root, directories, filenames in os.walk(str(source_root)):
        directories[:] = sorted(name for name in directories if name not in ignored)
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = Path(root) / filename
            relative = path.relative_to(source_root).as_posix()
            try:
                source_files[relative] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise PipelineError(f"Could not read source file {path}: {error}") from error

    if not source_files:
        raise PipelineError(f"No Python source files found under {source_root}.")
    return source_files


def _check_handoff_size(source_files: Dict[str, str], test_files: Dict[str, str]) -> None:
    size = sum(
        len(contents.encode("utf-8"))
        for files in (source_files, test_files)
        for contents in files.values()
    )
    if size > MAX_HANDOFF_BYTES:
        raise PipelineError(
            f"C4 handoff is {size} bytes; its source and tests must total no more than "
            f"{MAX_HANDOFF_BYTES} bytes."
        )


def _container_target(local_target: Path, explicit: Optional[str]) -> str:
    if explicit:
        return explicit.rstrip("/") or "/"
    try:
        relative = local_target.resolve().relative_to(REPO_ROOT)
    except ValueError as error:
        raise PipelineError(
            f"{local_target} is outside the repository mount; pass --container-target "
            "to specify the path visible to the component containers."
        ) from error
    suffix = relative.as_posix()
    return "/workspace" if suffix == "." else f"/workspace/{suffix}"


def _test_files_from_c3(response: Dict) -> Dict[str, str]:
    tests = response.get("tests", [])
    if not isinstance(tests, list):
        raise PipelineError("C3 /run response did not contain a tests list.")

    files: Dict[str, str] = {}
    for index, test in enumerate(tests, start=1):
        if not isinstance(test, dict) or not test.get("test_code", "").strip():
            continue
        function_name = re.sub(
            r"[^A-Za-z0-9_]+", "_", str(test.get("function_name", "generated"))
        ).strip("_") or "generated"
        file_name = f"test_{function_name}_{index}.py"
        files[file_name] = test["test_code"]
    if not files:
        raise PipelineError("C3 completed without returning any generated test code.")
    return files


def build_c3_payload(
    c2_response: Dict,
    sources: Dict[str, str],
    definitions: Dict[str, ast.AST],
    repository_path: str,
    min_risk_level: str = "MEDIUM",
    max_functions: Optional[int] = None,
) -> Dict:
    ranked = c2_response.get("ranked_functions", [])
    if not isinstance(ranked, list):
        raise PipelineError("C2 /predict response did not contain ranked_functions.")
    risk_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    minimum = risk_rank[min_risk_level]
    selected = [
        function for function in ranked
        if risk_rank.get(str(function.get("risk_level", "")).upper(), 3) <= minimum
    ]
    selected.sort(key=lambda function: function.get("priority_rank", 10**9))
    if max_functions is not None:
        selected = selected[:max_functions]
    if not selected:
        raise PipelineError(
            f"C2 returned no functions at or above the {min_risk_level} risk threshold."
        )

    segments = []
    for index, function in enumerate(selected, start=1):
        segments.append({
            "segment_id": f"seg-{index:03d}",
            "file_path": function["file_path"],
            "function_name": function["function_name"],
            "source_code": _source_for_ranked_function(function, sources, definitions),
            "risk_score": function["risk_score"],
            "cyclomatic_complexity": function.get("cyclomatic_complexity"),
            # C2's guidance, so C3 plans tests the same way as the Action path.
            "risk_level": function.get("risk_level"),
            "recommended_test_depth": function.get("recommended_test_depth"),
            "test_types": function.get("test_types"),
            "explanation_text": function.get("explanation_text") or "",
            "top_risk_factors": function.get("top_risk_factors") or [],
            "confidence": function.get("confidence", 1.0),
        })
    return {"repository_path": repository_path, "segments": segments}


def build_c4_payload(source_files: Dict[str, str], c3_response: Dict) -> Dict:
    test_files = _test_files_from_c3(c3_response)
    _check_handoff_size(source_files, test_files)
    return {"source_files": source_files, "test_files": test_files}


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the C1 -> C2 -> C3 -> C4 pipeline through the component APIs."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Local Python project directory to analyse and send to C4.",
    )
    parser.add_argument(
        "--container-target",
        default=None,
        help="Target directory as mounted inside C1/C3 containers; defaults to /workspace/<repo-relative-path>.",
    )
    parser.add_argument("--c1-url", default="http://localhost:8001")
    parser.add_argument("--c2-url", default="http://localhost:8002")
    parser.add_argument("--c3-url", default="http://localhost:8003")
    parser.add_argument("--c4-url", default="http://localhost:8004")
    parser.add_argument(
        "--min-risk-level",
        choices=["HIGH", "MEDIUM", "LOW"],
        default="MEDIUM",
        help="Lowest C2 risk tier to send to C3.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=None,
        help="Maximum number of highest-risk functions to send to C3.",
    )
    parser.add_argument("--request-timeout", type=int, default=1800)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for saving all four JSON API responses.",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> Dict:
    local_target = Path(args.target).expanduser().resolve()
    if not local_target.is_dir():
        raise PipelineError(f"Target must be an existing directory: {local_target}")
    if args.max_functions is not None and args.max_functions < 1:
        raise PipelineError("--max-functions must be greater than zero.")
    if args.request_timeout < 1:
        raise PipelineError("--request-timeout must be greater than zero.")

    container_target = _container_target(local_target, args.container_target)
    project_name = local_target.name

    print(f"[C1] Analysing {container_target}", flush=True)
    c1_response = post_json(
        f"{args.c1_url.rstrip('/')}/analyze-folder",
        {"folder_path": container_target},
        args.request_timeout,
    )
    c2_payload, sources, definitions = adapt_c1_response(
        c1_response, local_target, container_target, project_name
    )

    print(f"[C2] Scoring {len(c2_payload['functions'])} functions", flush=True)
    c2_response = post_json(
        f"{args.c2_url.rstrip('/')}/predict",
        c2_payload,
        args.request_timeout,
    )
    c3_payload = build_c3_payload(
        c2_response,
        sources,
        definitions,
        container_target,
        min_risk_level=args.min_risk_level,
        max_functions=args.max_functions,
    )

    print(f"[C3] Generating tests for {len(c3_payload['segments'])} functions", flush=True)
    c3_response = post_json(
        f"{args.c3_url.rstrip('/')}/run",
        c3_payload,
        args.request_timeout,
    )
    source_files = _source_files(local_target)
    c4_payload = build_c4_payload(source_files, c3_response)

    print(
        f"[C4] Evaluating {len(c4_payload['test_files'])} generated test file(s) in the Docker sandbox",
        flush=True,
    )
    c4_response = post_json(
        f"{args.c4_url.rstrip('/')}/api/evaluate",
        c4_payload,
        args.request_timeout,
    )

    result = {
        "c1": c1_response,
        "c2": c2_response,
        "c3": c3_response,
        "c4": c4_response,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Saved stage responses to {args.output}", flush=True)
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    try:
        result = run(args)
    except PipelineError as error:
        print(f"Pipeline failed: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Pipeline failed: {error}", file=sys.stderr)
        return 1

    c4 = result["c4"]
    print(
        json.dumps({
            "grade": c4.get("grade"),
            "quality_grade": c4.get("quality_grade"),
            "execution_status": c4.get("execution_status"),
            "test_results": c4.get("test_results"),
        }, indent=2),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
