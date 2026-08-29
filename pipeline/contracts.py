"""
The JSON contracts that connect one pipeline stage to the next.

Stages communicate only through these files, so any stage can be re-run or
replaced on its own as long as it keeps producing the same shape.

    stage 1  C1 static analysis
             -> artifacts/01_static_analysis.json      (C1's native format)
             -> artifacts/02_c2_input.json             (C2 BatchPredictRequest)

    stage 2  C2 ML risk detection
             -> artifacts/03_ml_output.json            (C2 tier_breakdown format)

    stage 3  C3 LLM test generation  [not wired yet]
             reads 03_ml_output.json via src/utils/ml_report_reader.py
"""

from pathlib import Path

# ── Artifact filenames ────────────────────────────────────────────────────────

STAGE1_RAW = "01_static_analysis.json"
STAGE1_C2_INPUT = "02_c2_input.json"
STAGE2_ML_OUTPUT = "03_ml_output.json"


# ── Component locations ───────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
C1_ROOT = REPO_ROOT / "components" / "c1_static_analysis"
C2_ROOT = REPO_ROOT / "components" / "c2_ml_risk" / "ml_risk_detector"

DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts"


# ── C2 input contract ─────────────────────────────────────────────────────────
# Mirrors FunctionMetricsRequest in
# components/c2_ml_risk/ml_risk_detector/api/predict_api.py.
#
# Keep this list in sync with that model. It is the single place that records
# where each of C2's 20 fields actually comes from.

# Fields C1 already produces, and the adapter simply forwards.
C2_FIELDS_FROM_C1 = [
    "function_name",           # FunctionInfo.name
    "file_path",               # analyze_file() "file" key
    "cyclomatic_complexity",   # FunctionInfo.cyclomatic_complexity
    "nesting_depth",           # FunctionInfo.nesting_depth
    "lines_of_code",           # FunctionInfo.lines_of_code
    "dependencies",            # FunctionInfo.dependencies
    "fan_out",                 # len(dependencies)
]

# Fields the adapter derives from the ast.FunctionDef node that C1's
# FunctionInfoAdapter already retains. See pipeline/extractors/function_metrics.py.
C2_FIELDS_FROM_AST = [
    "start_line",
    "end_line",
    "num_parameters",
    "num_return_statements",
    "num_exception_handlers",
    "num_loops",
    "num_conditionals",
    "has_recursion",
]

# Fields nothing upstream produces yet. Left at C2's own defaults for now.
#
# These are NOT cosmetic: bug_history is the single largest SHAP contributor in
# C2's own sample output, so risk scores stay compressed until they are filled.
# Backfilling them means mining git history per function (blame -> commits that
# touched the function's line range).
C2_FIELDS_DEFAULTED = [
    "commit_frequency",        # git log --follow on the function's line range
    "author_count",            # unique authors from that same log
    "bug_history",             # commits matching fix|bug|patch
    "days_since_last_change",  # now - last commit touching the range
    "fan_in",                  # needs a cross-file call graph
]

C2_DEFAULTS = {
    "commit_frequency": 0,
    "author_count": 1,
    "bug_history": 0,
    "days_since_last_change": 999,
    "fan_in": 0,
}

ALL_C2_FIELDS = C2_FIELDS_FROM_C1 + C2_FIELDS_FROM_AST + C2_FIELDS_DEFAULTED
