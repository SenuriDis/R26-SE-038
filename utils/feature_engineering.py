# convert AST or source code to ML metrics
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
 
@daaclass
class CodeMetrics:
    """
    Represents raw metrics for a single function/module.
    This is what Component 1 (Static Code Analysis) provides.
    """
    function_name: str
    file_path: str
    start_line: int
    end_line: int
 
    # Complexity metrics
    cyclomatic_complexity: int = 1
    nesting_depth: int = 0
    lines_of_code: int = 0
 
    # Coupling metrics
    fan_in: int = 0       # How many modules call this function
    fan_out: int = 0      # How many modules this function calls
    num_parameters: int = 0
 
    # Historical / process metrics
    commit_frequency: int = 0       # Number of commits touching this function
    author_count: int = 0           # Unique authors who modified it
    bug_history: int = 0            # Past bug fixes linked to this function
    days_since_last_change: int = 999
 
    # Structural features
    num_return_statements: int = 0
    num_exception_handlers: int = 0
    num_loops: int = 0
    num_conditionals: int = 0
    has_recursion: bool = False
 
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
 
 
class FeatureEngineer:
    """
    Transforms CodeMetrics into ML-ready feature vectors.
    Applies z-score normalisation and derived feature construction.
    """
 
    FEATURE_NAMES = [
        # Raw complexity
        "cyclomatic_complexity",
        "nesting_depth",
        "lines_of_code",
        "num_parameters",
        # Derived complexity
        "complexity_density",        # CC / LOC
        "complexity_nesting_product", # CC * nesting_depth
        # Coupling
        "fan_in",
        "fan_out",
        "total_coupling",            # fan_in + fan_out
        "coupling_ratio",            # fan_out / (fan_in + 1)
        # Historical
        "commit_frequency",
        "author_count",
        "bug_history",
        "days_since_last_change",
        "change_risk",               # commit_frequency * CC
        # Structural
        "num_return_statements",
        "num_exception_handlers",
        "num_loops",
        "num_conditionals",
        "has_recursion",
        # Aggregated
        "structural_complexity",     # loops + conditionals + exception_handlers
        "dependency_count",
    ]
 
    def __init__(self):
        self._fit_stats: Optional[Dict[str, Dict]] = None
 
    def extract_features(self, metrics: CodeMetrics) -> Dict[str, float]:
        """Extract and engineer features from a single CodeMetrics object."""
        loc = max(metrics.lines_of_code, 1)
        cc = metrics.cyclomatic_complexity
        fan_in = metrics.fan_in
        fan_out = metrics.fan_out
 
        features = {
            # Raw
            "cyclomatic_complexity": float(cc),
            "nesting_depth": float(metrics.nesting_depth),
            "lines_of_code": float(loc),
            "num_parameters": float(metrics.num_parameters),
            # Derived complexity
            "complexity_density": cc / loc,
            "complexity_nesting_product": float(cc * metrics.nesting_depth),
            # Coupling
            "fan_in": float(fan_in),
            "fan_out": float(fan_out),
            "total_coupling": float(fan_in + fan_out),
            "coupling_ratio": fan_out / (fan_in + 1),
            # Historical
            "commit_frequency": float(metrics.commit_frequency),
            "author_count": float(metrics.author_count),
            "bug_history": float(metrics.bug_history),
            "days_since_last_change": float(metrics.days_since_last_change),
            "change_risk": float(metrics.commit_frequency * cc),
            # Structural
            "num_return_statements": float(metrics.num_return_statements),
            "num_exception_handlers": float(metrics.num_exception_handlers),
            "num_loops": float(metrics.num_loops),
            "num_conditionals": float(metrics.num_conditionals),
            "has_recursion": float(metrics.has_recursion),
            # Aggregated
            "structural_complexity": float(
                metrics.num_loops + metrics.num_conditionals + metrics.num_exception_handlers
            ),
            "dependency_count": float(len(metrics.dependencies)),
        }
        return features
 
    def fit(self, metrics_list: List[CodeMetrics]) -> "FeatureEngineer":
        """Compute z-score stats from a list of CodeMetrics (training data)."""
        df = pd.DataFrame([self.extract_features(m) for m in metrics_list])
        self._fit_stats = {
            col: {"mean": df[col].mean(), "std": max(df[col].std(), 1e-8)}
            for col in df.columns
        }
        logger.info(f"FeatureEngineer fitted on {len(metrics_list)} samples.")
        return self
 
    def transform(self, metrics: CodeMetrics) -> np.ndarray:
        """Return a normalised feature vector for a single CodeMetrics object."""
        raw = self.extract_features(metrics)
        if self._fit_stats is None:
            # Return unnormalised if not fitted (inference without training data)
            return np.array([raw[f] for f in self.FEATURE_NAMES], dtype=np.float32)
 
        normalised = [
            (raw[f] - self._fit_stats[f]["mean"]) / self._fit_stats[f]["std"]
            for f in self.FEATURE_NAMES
        ]
        return np.array(normalised, dtype=np.float32)
 
    def transform_batch(self, metrics_list: List[CodeMetrics]) -> np.ndarray:
        """Transform a list of CodeMetrics into a 2D feature matrix."""
        return np.stack([self.transform(m) for m in metrics_list])
 
    @staticmethod
    def from_json(json_obj: Dict[str, Any]) -> CodeMetrics:
        """
        Parse a CodeMetrics object from a JSON dict.
        This is the interface that Component 1 provides.
        """
        return CodeMetrics(
            function_name=json_obj.get("function_name", "unknown"),
            file_path=json_obj.get("file_path", "unknown"),
            start_line=json_obj.get("start_line", 0),
            end_line=json_obj.get("end_line", 0),
            cyclomatic_complexity=json_obj.get("cyclomatic_complexity", 1),
            nesting_depth=json_obj.get("nesting_depth", 0),
            lines_of_code=json_obj.get("lines_of_code", 1),
            fan_in=json_obj.get("fan_in", 0),
            fan_out=json_obj.get("fan_out", 0),
            num_parameters=json_obj.get("num_parameters", 0),
            commit_frequency=json_obj.get("commit_frequency", 0),
            author_count=json_obj.get("author_count", 1),
            bug_history=json_obj.get("bug_history", 0),
            days_since_last_change=json_obj.get("days_since_last_change", 999),
            num_return_statements=json_obj.get("num_return_statements", 0),
            num_exception_handlers=json_obj.get("num_exception_handlers", 0),
            num_loops=json_obj.get("num_loops", 0),
            num_conditionals=json_obj.get("num_conditionals", 0),
            has_recursion=json_obj.get("has_recursion", False),
            dependencies=json_obj.get("dependencies", []),
        )
