import { useState } from "react";
import InputPanel from "../components/input/InputPanel";
import PipelineFlow from "../components/layout/PipelineFlow";
import TestCard from "../components/results/TestCard";
import ReviewCard from "../components/results/ReviewCard";
import StatsBar from "../components/results/StatsBar";
import { runPipeline } from "../api/pipelineApi";

const STEPS_COUNT = 5;

export default function Dashboard() {
  const [activeStep, setActiveStep] = useState(-1);
  const [isLoading,  setIsLoading]  = useState(false);
  const [results,    setResults]    = useState(null);
  const [error,      setError]      = useState(null);
  const [activeTab,  setActiveTab]  = useState("tests");

  const handleRun = async ({ repoPath, fnName, filePath, sourceCode, riskScore }) => {
    setIsLoading(true);
    setResults(null);
    setError(null);
    setActiveStep(0);

    // Animate pipeline steps while waiting
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step < STEPS_COUNT) setActiveStep(step);
    }, 3000);

    try {
      const data = await runPipeline({
        repository_path: repoPath,
        segments: [{
          function_name: fnName,
          file_path: filePath,
          source_code: sourceCode,
          risk_score: riskScore,
          cyclomatic_complexity: 3,
        }],
      });

      clearInterval(interval);
      setActiveStep(STEPS_COUNT);
      setResults(data);
      setActiveTab("tests");
    } catch (err) {
      clearInterval(interval);
      setActiveStep(-1);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const tabStyle = (name) => ({
    padding: "14px 20px",
    fontSize: "13px",
    fontWeight: 600,
    color: activeTab === name ? "#3b82f6" : "#64748b",
    cursor: "pointer",
    borderBottom: `2px solid ${activeTab === name ? "#3b82f6" : "transparent"}`,
    transition: "all 0.2s",
    userSelect: "none",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 60px)" }}>

      <PipelineFlow activeStep={activeStep} />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Left - Input */}
        <InputPanel onRun={handleRun} isLoading={isLoading} />

        {/* Right - Results */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Tabs */}
          <div style={{
            display: "flex",
            background: "#1a1f2e",
            borderBottom: "1px solid #2d3748",
            padding: "0 24px",
          }}>
            <div style={tabStyle("tests")} onClick={() => setActiveTab("tests")}>
              Generated Tests {results && `(${results.tests.length})`}
            </div>
            <div style={tabStyle("reviews")} onClick={() => setActiveTab("reviews")}>
              Code Review {results && `(${results.reviews.length})`}
            </div>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>

            {/* Error */}
            {error && (
              <div style={{
                background: "#7f1d1d", border: "1px solid #ef4444",
                borderRadius: "8px", padding: "14px 18px",
                fontSize: "13px", color: "#fca5a5", marginBottom: "16px",
              }}>
                ❌ {error}
              </div>
            )}

            {/* Empty state */}
            {!results && !error && !isLoading && (
              <div style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                height: "100%", color: "#4b5563", gap: "12px",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "48px" }}>
                  {activeTab === "tests" ? "🧪" : "🔍"}
                </div>
                <h3 style={{ fontSize: "16px", color: "#64748b" }}>
                  {activeTab === "tests" ? "No tests generated yet" : "No reviews yet"}
                </h3>
                <p style={{ fontSize: "13px", lineHeight: 1.6 }}>
                  Paste a Python function on the left and click Run Pipeline.
                </p>
              </div>
            )}

            {/* Loading state */}
            {isLoading && (
              <div style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                height: "100%", gap: "16px", color: "#64748b",
              }}>
                <div style={{
                  width: "40px", height: "40px",
                  border: "3px solid #2d3748",
                  borderTopColor: "#3b82f6",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}/>
                <p style={{ fontSize: "14px" }}>Pipeline running...</p>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            )}

            {/* Results */}
            {results && !isLoading && (
              <>
                <StatsBar data={results} />

                {activeTab === "tests" && results.tests.map((t, i) => (
                  <TestCard key={i} test={t} />
                ))}

                {activeTab === "reviews" && results.reviews.map((r, i) => (
                  <ReviewCard key={i} review={r} />
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}