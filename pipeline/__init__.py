"""
Integration pipeline for R26-SE-038.

Wires the four independently-developed components into one end-to-end flow:

    C1 Static Analysis  (Senuri)  -> components/c1_static_analysis
    C2 ML Risk Detector (Vihanga) -> components/c2_ml_risk
    C3 LLM Test Gen     (Harrish) -> not yet vendored
    C4 Test Evaluation  (Nisula)  -> not yet vendored

Stages hand data to each other as JSON files on disk (see pipeline/contracts.py).
No component's own source is modified by this package -- each stage imports the
component's modules and reuses them as-is.
"""

__all__ = ["contracts"]
