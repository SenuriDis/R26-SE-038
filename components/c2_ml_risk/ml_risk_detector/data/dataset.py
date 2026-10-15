"""Dataset loaders for ML Risk Predictor (Component 2).

Provides loaders for five real software-defect dataset families collected from
the PROMISE repository, NASA MDP, PSOWE, and the 2022 TSE CPDP benchmark,
plus the original synthetic generator kept as a CI / demo fallback.

Real dataset hierarchy (auto-discovered by load_all_real_datasets):
  data/NASA-promise-dataset/   — NASA MDP CSVs (cm1, jm1, kc1, kc2, pc1)
  data/Promise/                — Duplicate JM1 CSV (deduplicated automatically)
  data/PSOWE Dataset/          — CK OO-metrics CSVs (ant, camel, jedit …)
  data/SoftwareDefectDataset.csv — Halstead / LOC CSV (pre-normalised)
  data/2022_TSE_CPDP_DATA/SOFTLAB/  — McCabe ARFF files (ar1–ar6)
  data/2022_TSE_CPDP_DATA/NASA/     — McCabe ARFF files (cm1, mw1, PC1–4)
  (AEEEM / ReLink ARFFs are skipped — malformed headers logged as warnings)

Every public function returns the same (X, y, metrics_list) triple that the
rest of the pipeline (FeatureEngineer, MLRiskDetector, TestPrioritizer, API)
already expects — no other files need to change.
"""

import os
import glob
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List
from utils.feature_engineering import CodeMetrics
import logging

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "cyclomatic_complexity", "nesting_depth", "lines_of_code", "num_parameters",
    "complexity_density", "complexity_nesting_product",
    "fan_in", "fan_out", "total_coupling", "coupling_ratio",
    "commit_frequency", "author_count", "bug_history", "days_since_last_change",
    "change_risk",
    "num_return_statements", "num_exception_handlers", "num_loops", "num_conditionals",
    "has_recursion", "structural_complexity", "dependency_count",
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_feature_row(
    cc: float, nesting: float, loc: float, num_params: float,
    fan_in: float, fan_out: float, commit_freq: float, author_cnt: float,
    bug_hist: float, days_last: float, num_returns: float,
    num_exc: float, num_loops: float, num_conds: float,
    has_rec: float, dep_count: float,
) -> dict:
    """Compute the full derived-feature dict from raw metric values."""
    loc = max(loc, 1.0)
    return {
        "cyclomatic_complexity":    cc,
        "nesting_depth":            nesting,
        "lines_of_code":            loc,
        "num_parameters":           num_params,
        "complexity_density":       cc / loc,
        "complexity_nesting_product": cc * nesting,
        "fan_in":                   fan_in,
        "fan_out":                  fan_out,
        "total_coupling":           fan_in + fan_out,
        "coupling_ratio":           fan_out / (fan_in + 1),
        "commit_frequency":         commit_freq,
        "author_count":             author_cnt,
        "bug_history":              bug_hist,
        "days_since_last_change":   days_last,
        "change_risk":              commit_freq * cc,
        "num_return_statements":    num_returns,
        "num_exception_handlers":   num_exc,
        "num_loops":                num_loops,
        "num_conditionals":         num_conds,
        "has_recursion":            has_rec,
        "structural_complexity":    num_loops + num_conds + num_exc,
        "dependency_count":         dep_count,
    }


def _row_to_codemetrics(row: dict, idx: int, source: str) -> CodeMetrics:
    """Convert a feature-row dict to a CodeMetrics object for FeatureEngineer."""
    return CodeMetrics(
        function_name=f"{source}_func_{idx}",
        file_path=f"{source}_module_{idx // 20}.py",
        start_line=1,
        end_line=max(int(row["lines_of_code"]), 1),
        cyclomatic_complexity=max(int(row["cyclomatic_complexity"]), 1),
        nesting_depth=max(int(row["nesting_depth"]), 0),
        lines_of_code=max(int(row["lines_of_code"]), 1),
        fan_in=max(int(row["fan_in"]), 0),
        fan_out=max(int(row["fan_out"]), 0),
        num_parameters=max(int(row["num_parameters"]), 0),
        commit_frequency=max(int(row["commit_frequency"]), 0),
        author_count=max(int(row["author_count"]), 1),
        bug_history=max(int(row["bug_history"]), 0),
        days_since_last_change=max(int(row["days_since_last_change"]), 1),
        num_return_statements=max(int(row["num_return_statements"]), 0),
        num_exception_handlers=max(int(row["num_exception_handlers"]), 0),
        num_loops=max(int(row["num_loops"]), 0),
        num_conditionals=max(int(row["num_conditionals"]), 0),
        has_recursion=bool(row["has_recursion"]),
        dependencies=[f"dep_{j}" for j in range(max(int(row["dependency_count"]), 0))],
    )


def _finalise(rows: list, labels_raw: list, source: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """Convert raw rows + labels into the standard (X, y, metrics_list) triple."""
    df = pd.DataFrame(rows)
    y = pd.Series(labels_raw, dtype=int)
    metrics_list = [_row_to_codemetrics(r, i, source) for i, r in enumerate(rows)]
    df_clean = df.dropna()
    y_clean = y[df_clean.index].reset_index(drop=True)
    df_clean = df_clean.reset_index(drop=True)
    metrics_clean = [metrics_list[i] for i in df_clean.index.tolist()] if len(df_clean) < len(df) else metrics_list
    logger.info(
        f"[{source}] loaded {len(df_clean)} samples "
        f"({int(y_clean.sum())} defective / {int((y_clean == 0).sum())} clean)"
    )
    return df_clean[FEATURE_COLUMNS], y_clean, metrics_clean


# ─────────────────────────────────────────────────────────────────────────────
# Schema A — NASA / PROMISE McCabe + Halstead CSVs
# Files: NASA-promise-dataset/{cm1,jm1,kc1,kc2,pc1}.csv
#        Promise/jm1.csv
# Columns: loc, v(g), iv(g), branchCount, uniq_Op, total_Op, defects/problems
# ─────────────────────────────────────────────────────────────────────────────

def load_nasa_promise_csv(path: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Load a NASA / PROMISE McCabe+Halstead CSV file.

    Supported label columns: 'defects' (True/False), 'problems' ('yes'/'no').
    Cyclomatic complexity → v(g), nesting proxy → iv(g), conditionals → branchCount.
    Historical metrics (commit_frequency, author_count, bug_history,
    days_since_last_change) are not present in this schema; safe dataset-level
    defaults are derived from the label column to preserve signal direction.
    """
    source = os.path.splitext(os.path.basename(path))[0]
    df = pd.read_csv(path)

    # Normalise column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Detect label column
    label_col = None
    for candidate in ("defects", "problems"):
        if candidate in df.columns:
            label_col = candidate
            break
    if label_col is None:
        raise ValueError(f"[{source}] No recognised label column in {path}")

    # Parse labels robustly
    raw_labels = df[label_col].astype(str).str.strip().str.lower()
    labels = raw_labels.map(lambda v: 1 if v in ("true", "yes", "1", "1.0") else 0)

    rows = []
    for i, row in df.iterrows():
        cc      = max(float(row.get("v(g)", 1)), 1.0)
        nesting = max(float(row.get("iv(g)", 1)), 0.0)   # essential complexity ≈ nesting proxy
        loc     = max(float(row.get("loc", 10)), 1.0)
        params  = max(float(row.get("uniq_opnd", row.get("total_opnd", 2))), 0.0)
        conds   = max(float(row.get("branchcount", row.get("branchcount", 0))), 0.0)
        # Halstead-derived fan-out proxy: uniq_Op / 5
        fan_out = max(float(row.get("uniq_op", 5)) / 5.0, 0.0)
        fan_in  = max(float(row.get("uniq_opnd", 3)) / 3.0, 0.0)

        feat = _build_feature_row(
            cc=cc, nesting=nesting, loc=loc, num_params=params,
            fan_in=fan_in, fan_out=fan_out,
            commit_freq=0.0, author_cnt=1.0, bug_hist=0.0, days_last=180.0,
            num_returns=1.0, num_exc=0.0, num_loops=max(conds / 3.0, 0.0),
            num_conds=conds, has_rec=0.0, dep_count=fan_out,
        )
        rows.append(feat)

    return _finalise(rows, labels.tolist(), source)


# ─────────────────────────────────────────────────────────────────────────────
# Schema B — PSOWE CK Object-Oriented Metrics CSVs
# Files: PSOWE Dataset/{ant-1.7, camel-1.0, camel-1.6, jedit-*, …}.csv
#        PSOWE Dataset/data_{arc, ivy-2.0, prop-6, redaktor}.csv
# Columns: wmc, max_cc, avg_cc, cbo, rfc, lcom, ca, ce, npm, loc, bug
# ─────────────────────────────────────────────────────────────────────────────

def load_psowe_csv(path: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Load a PSOWE CK (Chidamber-Kemerer) object-oriented metrics CSV.

    Column mapping:
      max_cc / wmc  → cyclomatic_complexity
      loc           → lines_of_code
      ca            → fan_in  (afferent coupling — modules that use this class)
      ce / cbo      → fan_out (efferent coupling — modules this class uses)
      npm           → num_parameters (public method count ≈ interface size)
      rfc           → num_conditionals proxy (response for class)
      bug (count)   → label (>0 → defective)
    """
    source = os.path.splitext(os.path.basename(path))[0]
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "bug" not in df.columns:
        raise ValueError(f"[{source}] 'bug' column not found in {path}")

    labels = (df["bug"].fillna(0).astype(float) > 0).astype(int)

    rows = []
    for i, row in df.iterrows():
        # Prefer max_cc (per-method max) over wmc (sum) for CC proxy
        cc = max(float(row.get("max_cc", row.get("wmc", 1))), 1.0)
        loc = max(float(row.get("loc", 10)), 1.0)
        fan_in  = max(float(row.get("ca", 0)), 0.0)
        fan_out = max(float(row.get("ce", row.get("cbo", 0))), 0.0)
        npm     = max(float(row.get("npm", 1)), 0.0)
        rfc     = max(float(row.get("rfc", 0)), 0.0)
        avg_cc  = max(float(row.get("avg_cc", cc / max(npm, 1))), 0.0)
        nesting = max(avg_cc / max(cc, 1) * 3.0, 0.0)   # nesting proxy from avg/max CC ratio

        feat = _build_feature_row(
            cc=cc, nesting=nesting, loc=loc, num_params=npm,
            fan_in=fan_in, fan_out=fan_out,
            commit_freq=0.0, author_cnt=1.0, bug_hist=0.0, days_last=180.0,
            num_returns=1.0, num_exc=0.0, num_loops=max(rfc / 10.0, 0.0),
            num_conds=max(rfc / 5.0, 0.0), has_rec=0.0, dep_count=fan_out,
        )
        rows.append(feat)

    return _finalise(rows, labels.tolist(), source)


# ─────────────────────────────────────────────────────────────────────────────
# Schema C — SoftwareDefectDataset (pre-normalised 0-1)
# File: SoftwareDefectDataset.csv
# Columns: LOC, CYCLO, LENGTH, VOLUME, DIFFICULTY,
#          INT_FAN_IN, INT_FAN_OUT, NUM_OPERATORS, NUM_OPERANDS,
#          BRANCH_COUNT, DEFECT_LABEL
# ─────────────────────────────────────────────────────────────────────────────

def load_software_defect_csv(path: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Load the SoftwareDefectDataset CSV (features pre-normalised to [0, 1]).

    Values are rescaled to realistic metric ranges before feature engineering
    so z-score normalisation in FeatureEngineer produces meaningful statistics.
    """
    source = "SoftwareDefectDataset"
    df = pd.read_csv(path)
    df.columns = [c.strip().upper() for c in df.columns]

    labels = df["DEFECT_LABEL"].fillna(0).astype(int)

    rows = []
    for i, row in df.iterrows():
        # Rescale from [0,1] to realistic metric ranges
        cc      = max(float(row.get("CYCLO", 0.05)) * 20.0, 1.0)   # 0–20 range
        loc     = max(float(row.get("LOC",   0.1))  * 200.0, 1.0)  # 0–200 range
        fan_in  = max(float(row.get("INT_FAN_IN",  0)) * 10.0, 0.0)
        fan_out = max(float(row.get("INT_FAN_OUT", 0)) * 10.0, 0.0)
        conds   = max(float(row.get("BRANCH_COUNT", 0)) * 15.0, 0.0)
        params  = max(float(row.get("NUM_OPERANDS", 0.1)) * 8.0, 0.0)
        diff    = max(float(row.get("DIFFICULTY", 0.1)), 0.0)       # 0–1 difficulty index
        nesting = max(diff * 5.0, 0.0)                               # nesting proxy from difficulty

        feat = _build_feature_row(
            cc=cc, nesting=nesting, loc=loc, num_params=params,
            fan_in=fan_in, fan_out=fan_out,
            commit_freq=0.0, author_cnt=1.0, bug_hist=0.0, days_last=180.0,
            num_returns=1.0, num_exc=0.0, num_loops=max(conds / 3.0, 0.0),
            num_conds=conds, has_rec=0.0, dep_count=fan_out,
        )
        rows.append(feat)

    return _finalise(rows, labels.tolist(), source)


# ─────────────────────────────────────────────────────────────────────────────
# Schema D — SOFTLAB ARFF (2022 TSE CPDP benchmark)
# Files: 2022_TSE_CPDP_DATA/SOFTLAB/ar{1,3,4,5,6}.arff
# Columns: total_loc, cyclomatic_complexity, formal_parameters,
#          condition_count, call_pairs, branch_count, defects ('clean'/'defect')
# ─────────────────────────────────────────────────────────────────────────────

def load_softlab_arff(path: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Load a SOFTLAB ARFF file from the 2022 TSE CPDP benchmark.

    Best column match of all ARFF datasets — has cyclomatic_complexity,
    formal_parameters, condition_count, call_pairs, and total_loc directly.
    Label: 'clean' → 0, 'defect' → 1.
    """
    try:
        from scipy.io import arff
    except ImportError:
        logger.warning("scipy not installed — skipping SOFTLAB ARFF loader. Run: pip install scipy")
        return pd.DataFrame(), pd.Series(dtype=int), []

    source = os.path.splitext(os.path.basename(path))[0]
    try:
        data, _ = arff.loadarff(path)
        df = pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"[{source}] Failed to parse ARFF {path}: {e} — skipping")
        return pd.DataFrame(), pd.Series(dtype=int), []

    # Decode byte strings
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.decode("utf-8", errors="replace")

    df.columns = [c.strip().lower() for c in df.columns]

    if "defects" not in df.columns:
        logger.warning(f"[{source}] No 'defects' column found — skipping {path}")
        return pd.DataFrame(), pd.Series(dtype=int), []

    raw_labels = df["defects"].astype(str).str.strip().str.lower()
    labels = raw_labels.map(lambda v: 0 if v in ("clean", "0", "false", "no") else 1)

    rows = []
    for i, row in df.iterrows():
        cc      = max(float(row.get("cyclomatic_complexity", 1)), 1.0)
        loc     = max(float(row.get("total_loc", row.get("executable_loc", 10))), 1.0)
        params  = max(float(row.get("formal_parameters", 0)), 0.0)
        conds   = max(float(row.get("condition_count", row.get("multiple_condition_count", 0))), 0.0)
        calls   = max(float(row.get("call_pairs", 0)), 0.0)
        branch  = max(float(row.get("branch_count", conds)), 0.0)
        nesting = max(float(row.get("decision_count", conds / max(cc, 1))), 0.0)
        fan_out = max(calls, 0.0)
        fan_in  = max(float(row.get("unique_operators", 0)) / 5.0, 0.0)

        feat = _build_feature_row(
            cc=cc, nesting=nesting, loc=loc, num_params=params,
            fan_in=fan_in, fan_out=fan_out,
            commit_freq=0.0, author_cnt=1.0, bug_hist=0.0, days_last=180.0,
            num_returns=1.0, num_exc=0.0, num_loops=max(branch / 3.0, 0.0),
            num_conds=conds, has_rec=0.0, dep_count=fan_out,
        )
        rows.append(feat)

    return _finalise(rows, labels.tolist(), source)


# ─────────────────────────────────────────────────────────────────────────────
# Schema E — CPDP / NASA ARFF (2022 TSE benchmark NASA subset)
# Files: 2022_TSE_CPDP_DATA/NASA/{cm1,mw1,PC1,PC3,PC4}.arff
# Same McCabe + Halstead schema as the PROMISE CSVs but in ARFF format.
# Label: last column, values like b'Y' / b'N' or b'true' / b'false'
# ─────────────────────────────────────────────────────────────────────────────

def load_cpdp_nasa_arff(path: str) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Load a NASA ARFF file from the 2022 TSE CPDP benchmark.

    Column schema mirrors the PROMISE CSVs (McCabe + Halstead).
    Label column is always last; values are decoded byte-strings.
    """
    try:
        from scipy.io import arff
    except ImportError:
        logger.warning("scipy not installed — skipping NASA ARFF loader. Run: pip install scipy")
        return pd.DataFrame(), pd.Series(dtype=int), []

    source = os.path.splitext(os.path.basename(path))[0]
    try:
        data, _ = arff.loadarff(path)
        df = pd.DataFrame(data)
    except Exception as e:
        logger.warning(f"[{source}] Failed to parse ARFF {path}: {e} — skipping")
        return pd.DataFrame(), pd.Series(dtype=int), []

    # Decode byte strings
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.decode("utf-8", errors="replace")

    df.columns = [c.strip().lower() for c in df.columns]

    # Label is always the last column
    label_col = df.columns[-1]
    raw_labels = df[label_col].astype(str).str.strip().str.lower()
    labels = raw_labels.map(lambda v: 1 if v in ("y", "yes", "true", "1", "1.0") else 0)

    rows = []
    for i, row in df.iterrows():
        # McCabe columns — same as PROMISE CSV Schema A
        cc      = max(float(row.get("v(g)", row.get("sumcyclomatic", row.get("maxcyclomatic", 1)))), 1.0)
        nesting = max(float(row.get("iv(g)", row.get("maxcyclomaticmodified", 1))), 0.0)
        loc     = max(float(row.get("loc", row.get("linecnt", row.get("locdecl", 10)))), 1.0)
        params  = max(float(row.get("uniq_opnd", row.get("total_opnd", 2))), 0.0)
        conds   = max(float(row.get("branchcount", row.get("countbranch", 0))), 0.0)
        fan_out = max(float(row.get("uniq_op", 5)) / 5.0, 0.0)
        fan_in  = max(float(row.get("uniq_opnd", 3)) / 3.0, 0.0)

        feat = _build_feature_row(
            cc=cc, nesting=nesting, loc=loc, num_params=params,
            fan_in=fan_in, fan_out=fan_out,
            commit_freq=0.0, author_cnt=1.0, bug_hist=0.0, days_last=180.0,
            num_returns=1.0, num_exc=0.0, num_loops=max(conds / 3.0, 0.0),
            num_conds=conds, has_rec=0.0, dep_count=fan_out,
        )
        rows.append(feat)

    return _finalise(rows, labels.tolist(), source)


# ─────────────────────────────────────────────────────────────────────────────
# Master aggregator — discovers and loads all real datasets
# ─────────────────────────────────────────────────────────────────────────────

def load_all_real_datasets(
    data_dir: str = "data",
) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series], List[CodeMetrics]]:
    """
    Auto-discover and load every real dataset found under `data_dir`.

    Walks the known sub-paths, calls the appropriate schema loader for each
    file, concatenates results, removes duplicates, shuffles, and returns the
    standard (X, y, metrics_list) triple ready for train.py.

    Returns (None, None, []) if no files are found (caller should fall back
    to generate_synthetic_dataset).
    """
    all_X: List[pd.DataFrame] = []
    all_y: List[pd.Series] = []
    all_metrics: List[CodeMetrics] = []

    # ── Schema A: NASA-promise-dataset CSVs ──────────────────────────────────
    nasa_promise_dir = os.path.join(data_dir, "NASA-promise-dataset")
    if os.path.isdir(nasa_promise_dir):
        for path in sorted(glob.glob(os.path.join(nasa_promise_dir, "*.csv"))):
            try:
                X, y, m = load_nasa_promise_csv(path)
                if len(X) > 0:
                    all_X.append(X); all_y.append(y); all_metrics.extend(m)
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

    # ── Schema A (duplicate JM1): Promise/ ──────────────────────────────────
    # Only load if it is not already covered by the NASA-promise-dataset folder
    promise_dir = os.path.join(data_dir, "Promise")
    if os.path.isdir(promise_dir):
        nasa_names = {os.path.basename(p) for p in glob.glob(os.path.join(nasa_promise_dir, "*.csv"))} \
            if os.path.isdir(nasa_promise_dir) else set()
        for path in sorted(glob.glob(os.path.join(promise_dir, "*.csv"))):
            if os.path.basename(path) in nasa_names:
                logger.info(f"[Promise] Skipping {os.path.basename(path)} — already loaded from NASA-promise-dataset")
                continue
            try:
                X, y, m = load_nasa_promise_csv(path)
                if len(X) > 0:
                    all_X.append(X); all_y.append(y); all_metrics.extend(m)
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

    # ── Schema B: PSOWE CK OO metrics ────────────────────────────────────────
    psowe_dir = os.path.join(data_dir, "PSOWE Dataset")
    if os.path.isdir(psowe_dir):
        for path in sorted(glob.glob(os.path.join(psowe_dir, "*.csv"))):
            try:
                X, y, m = load_psowe_csv(path)
                if len(X) > 0:
                    all_X.append(X); all_y.append(y); all_metrics.extend(m)
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

    # ── Schema C: SoftwareDefectDataset ──────────────────────────────────────
    sdd_path = os.path.join(data_dir, "SoftwareDefectDataset.csv")
    if os.path.isfile(sdd_path):
        try:
            X, y, m = load_software_defect_csv(sdd_path)
            if len(X) > 0:
                all_X.append(X); all_y.append(y); all_metrics.extend(m)
        except Exception as e:
            logger.warning(f"Skipping SoftwareDefectDataset.csv: {e}")

    # ── Schema D: SOFTLAB ARFF ────────────────────────────────────────────────
    softlab_dir = os.path.join(data_dir, "2022_TSE_CPDP_DATA", "SOFTLAB")
    if os.path.isdir(softlab_dir):
        for path in sorted(glob.glob(os.path.join(softlab_dir, "*.arff"))):
            try:
                X, y, m = load_softlab_arff(path)
                if len(X) > 0:
                    all_X.append(X); all_y.append(y); all_metrics.extend(m)
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

    # ── Schema E: CPDP / NASA ARFF ───────────────────────────────────────────
    cpdp_nasa_dir = os.path.join(data_dir, "2022_TSE_CPDP_DATA", "NASA")
    if os.path.isdir(cpdp_nasa_dir):
        for path in sorted(glob.glob(os.path.join(cpdp_nasa_dir, "*.arff"))):
            try:
                X, y, m = load_cpdp_nasa_arff(path)
                if len(X) > 0:
                    all_X.append(X); all_y.append(y); all_metrics.extend(m)
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

    # ── AEEEM / ReLink: intentionally skipped (malformed ARFF headers) ────────
    for skip_dir in ("AEEEM", "ReLink"):
        skip_path = os.path.join(data_dir, "2022_TSE_CPDP_DATA", skip_dir)
        if os.path.isdir(skip_path):
            logger.warning(
                f"[{skip_dir}] Skipped — ARFF files contain malformed headers "
                f"incompatible with scipy.io.arff. ({skip_path})"
            )

    # ── Combine ───────────────────────────────────────────────────────────────
    if not all_X:
        logger.warning("load_all_real_datasets: no datasets found — returning empty result")
        return None, None, []

    X_combined = pd.concat(all_X, ignore_index=True)
    y_combined = pd.concat(all_y, ignore_index=True)

    # Shuffle (reproducible)
    rng = np.random.RandomState(42)
    idx = rng.permutation(len(X_combined))
    X_combined = X_combined.iloc[idx].reset_index(drop=True)
    y_combined = y_combined.iloc[idx].reset_index(drop=True)
    all_metrics = [all_metrics[i] for i in idx]

    total = len(X_combined)
    n_def = int(y_combined.sum())
    logger.info(
        f"load_all_real_datasets: combined {total} samples from "
        f"{len(all_X)} source(s) — "
        f"{n_def} defective ({n_def/total*100:.1f}%) / "
        f"{total - n_def} clean ({(total-n_def)/total*100:.1f}%)"
    )
    return X_combined, y_combined, all_metrics


# ─────────────────────────────────────────────────────────────────────────────
# Original synthetic generator — kept as CI / demo fallback
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_dataset(
    n_samples: int = 2000,
    defect_ratio: float = 0.15,  # Realistic: ~15% of functions are defect-prone
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Generate synthetic code metrics resembling PROMISE/NASA MDP datasets.
    Returns (features_df, labels, metrics_list).

    Kept as a fallback for CI pipelines and demo environments where
    the real dataset files may not be present.

    Defective functions tend to have:
    - High cyclomatic complexity (>10)
    - High nesting depth (>3)
    - High commit frequency with many authors
    - High fan-out coupling
    - Prior bug history
    """
    rng = np.random.RandomState(random_state)
    n_defective = int(n_samples * defect_ratio)
    n_clean = n_samples - n_defective

    def sample_clean(n):
        return {
            "cyclomatic_complexity": rng.randint(1, 8, n),
            "nesting_depth": rng.randint(0, 3, n),
            "lines_of_code": rng.randint(5, 60, n),
            "fan_in": rng.randint(0, 5, n),
            "fan_out": rng.randint(0, 4, n),
            "num_parameters": rng.randint(0, 5, n),
            "commit_frequency": rng.randint(0, 8, n),
            "author_count": rng.randint(1, 3, n),
            "bug_history": rng.randint(0, 1, n),
            "days_since_last_change": rng.randint(30, 999, n),
            "num_return_statements": rng.randint(1, 3, n),
            "num_exception_handlers": rng.randint(0, 1, n),
            "num_loops": rng.randint(0, 2, n),
            "num_conditionals": rng.randint(0, 4, n),
            "has_recursion": rng.randint(0, 2, n),
            "dependency_count": rng.randint(0, 3, n),
        }

    def sample_defective(n):
        return {
            "cyclomatic_complexity": rng.randint(8, 30, n),
            "nesting_depth": rng.randint(3, 8, n),
            "lines_of_code": rng.randint(40, 300, n),
            "fan_in": rng.randint(0, 6, n),
            "fan_out": rng.randint(5, 15, n),
            "num_parameters": rng.randint(4, 12, n),
            "commit_frequency": rng.randint(8, 40, n),
            "author_count": rng.randint(2, 8, n),
            "bug_history": rng.randint(1, 6, n),
            "days_since_last_change": rng.randint(1, 60, n),
            "num_return_statements": rng.randint(2, 8, n),
            "num_exception_handlers": rng.randint(0, 5, n),
            "num_loops": rng.randint(2, 8, n),
            "num_conditionals": rng.randint(5, 20, n),
            "has_recursion": rng.randint(0, 2, n),
            "dependency_count": rng.randint(3, 12, n),
        }

    clean_data = sample_clean(n_clean)
    defect_data = sample_defective(n_defective)

    def build_df(data, label, start_idx):
        n = len(data["cyclomatic_complexity"])
        loc = np.maximum(data["lines_of_code"], 1)
        cc = data["cyclomatic_complexity"]
        fan_in = data["fan_in"]
        fan_out = data["fan_out"]

        rows = []
        metrics_list = []
        for i in range(n):
            m = CodeMetrics(
                function_name=f"func_{start_idx + i}",
                file_path=f"module_{(start_idx + i) // 20}.py",
                start_line=1,
                end_line=int(loc[i]),
                cyclomatic_complexity=int(cc[i]),
                nesting_depth=int(data["nesting_depth"][i]),
                lines_of_code=int(loc[i]),
                fan_in=int(fan_in[i]),
                fan_out=int(fan_out[i]),
                num_parameters=int(data["num_parameters"][i]),
                commit_frequency=int(data["commit_frequency"][i]),
                author_count=int(data["author_count"][i]),
                bug_history=int(data["bug_history"][i]),
                days_since_last_change=int(data["days_since_last_change"][i]),
                num_return_statements=int(data["num_return_statements"][i]),
                num_exception_handlers=int(data["num_exception_handlers"][i]),
                num_loops=int(data["num_loops"][i]),
                num_conditionals=int(data["num_conditionals"][i]),
                has_recursion=bool(data["has_recursion"][i]),
                dependencies=[f"dep_{j}" for j in range(int(data["dependency_count"][i]))],
            )
            metrics_list.append(m)
            row = {
                "cyclomatic_complexity": float(cc[i]),
                "nesting_depth": float(data["nesting_depth"][i]),
                "lines_of_code": float(loc[i]),
                "num_parameters": float(data["num_parameters"][i]),
                "complexity_density": float(cc[i] / loc[i]),
                "complexity_nesting_product": float(cc[i] * data["nesting_depth"][i]),
                "fan_in": float(fan_in[i]),
                "fan_out": float(fan_out[i]),
                "total_coupling": float(fan_in[i] + fan_out[i]),
                "coupling_ratio": float(fan_out[i] / (fan_in[i] + 1)),
                "commit_frequency": float(data["commit_frequency"][i]),
                "author_count": float(data["author_count"][i]),
                "bug_history": float(data["bug_history"][i]),
                "days_since_last_change": float(data["days_since_last_change"][i]),
                "change_risk": float(data["commit_frequency"][i] * cc[i]),
                "num_return_statements": float(data["num_return_statements"][i]),
                "num_exception_handlers": float(data["num_exception_handlers"][i]),
                "num_loops": float(data["num_loops"][i]),
                "num_conditionals": float(data["num_conditionals"][i]),
                "has_recursion": float(data["has_recursion"][i]),
                "structural_complexity": float(
                    data["num_loops"][i] + data["num_conditionals"][i] + data["num_exception_handlers"][i]
                ),
                "dependency_count": float(data["dependency_count"][i]),
                "label": label,
            }
            rows.append(row)
        return rows, metrics_list

    clean_rows, clean_metrics = build_df(clean_data, 0, 0)
    defect_rows, defect_metrics = build_df(defect_data, 1, n_clean)

    all_rows = clean_rows + defect_rows
    all_metrics = clean_metrics + defect_metrics

    # Shuffle
    idx = rng.permutation(len(all_rows))
    all_rows = [all_rows[i] for i in idx]
    all_metrics = [all_metrics[i] for i in idx]

    df = pd.DataFrame(all_rows)
    labels = df.pop("label")

    logger.info(
        f"Generated {len(df)} samples: {int(labels.sum())} defective ({defect_ratio*100:.0f}%), "
        f"{int((1-labels).sum())} clean"
    )
    return df, labels, all_metrics
