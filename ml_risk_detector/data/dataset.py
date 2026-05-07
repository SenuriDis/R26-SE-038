"""Generates synthetic training data that mirrors real PROMISE / NASA MDP defect datasets.
I am using this for demo/testing until real repository mining is implemented in future

Real pipeline: GitPython mines 200+ repos → Component 1 extracts AST metrics → this module loads them.
"""

import numpy as np
import pandas as pd
from typing import Tuple, List
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


def generate_synthetic_dataset(
    n_samples: int = 2000,
    defect_ratio: float = 0.15,  # Realistic: ~15% of functions are defect-prone
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.Series, List[CodeMetrics]]:
    """
    Generate synthetic code metrics resembling PROMISE/NASA MDP datasets.
    Returns (features_df, labels, metrics_list).

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