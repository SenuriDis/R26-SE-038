import { useState } from "react";

const DEFAULT_REPO = "D:\\Year 4 Sem 1\\temp_repos\\requests\\src\\requests";
const DEFAULT_CODE = `def divide(a, b):\n    return a / b`;

export default function InputPanel({ onRun, isLoading }) {
  const [repoPath,   setRepoPath]   = useState(DEFAULT_REPO);
  const [fnName,     setFnName]     = useState("divide");
  const [filePath,   setFilePath]   = useState("sample_project/calculator.py");
  const [sourceCode, setSourceCode] = useState(DEFAULT_CODE);
  const [riskScore,  setRiskScore]  = useState(0.87);

  const handleSubmit = () => {
    if (!fnName.trim() || !sourceCode.trim()) {
      alert("Please fill in function name and source code.");
      return;
    }
    onRun({ repoPath, fnName, filePath, sourceCode, riskScore });
  };

  const inputStyle = {
    background: "#0f1117",
    border: "1px solid #2d3748",
    borderRadius: "8px",
    color: "#e2e8f0",
    fontSize: "13px",
    padding: "10px 12px",
    outline: "none",
    width: "100%",
    fontFamily: "'Segoe UI', sans-serif",
  };

  const labelStyle = {
    fontSize: "12px",
    color: "#94a3b8",
    fontWeight: 600,
    marginBottom: "6px",
    display: "block",
  };

  const sectionTitle = {
    fontSize: "11px",
    fontWeight: 700,
    color: "#64748b",
    letterSpacing: "1.5px",
    textTransform: "uppercase",
    marginBottom: "14px",
  };

  return (
    <div style={{
      background: "#1a1f2e",
      borderRight: "1px solid #2d3748",
      padding: "24px",
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
      gap: "24px",
      width: "400px",
      minWidth: "400px",
    }}>

      {/* Repository */}
      <div>
        <p style={sectionTitle}>Repository</p>
        <label style={labelStyle}>Repository Path</label>
        <input
          style={inputStyle}
          value={repoPath}
          onChange={e => setRepoPath(e.target.value)}
          placeholder="Absolute path to your repo"
        />
      </div>

      {/* Code Segment */}
      <div>
        <p style={sectionTitle}>Code Segment</p>

        <div style={{ marginBottom: "12px" }}>
          <label style={labelStyle}>Function Name</label>
          <input
            style={inputStyle}
            value={fnName}
            onChange={e => setFnName(e.target.value)}
            placeholder="e.g. divide"
          />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <label style={labelStyle}>File Path (relative)</label>
          <input
            style={inputStyle}
            value={filePath}
            onChange={e => setFilePath(e.target.value)}
            placeholder="e.g. src/calculator.py"
          />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <label style={labelStyle}>Source Code</label>
          <textarea
            style={{
              ...inputStyle,
              fontFamily: "'Cascadia Code', 'Consolas', monospace",
              fontSize: "12px",
              resize: "vertical",
              minHeight: "160px",
            }}
            value={sourceCode}
            onChange={e => setSourceCode(e.target.value)}
            placeholder="Paste the function code here"
          />
        </div>

        <div>
          <label style={labelStyle}>
            Risk Score (from ML Component) — {riskScore.toFixed(2)}
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <input
              type="range"
              min={0} max={1} step={0.01}
              value={riskScore}
              onChange={e => setRiskScore(parseFloat(e.target.value))}
              style={{ flex: 1, accentColor: "#3b82f6" }}
            />
            <span style={{
              background: "#1e3a5f",
              color: "#93c5fd",
              fontWeight: 700,
              fontSize: "13px",
              padding: "4px 10px",
              borderRadius: "6px",
              minWidth: "48px",
              textAlign: "center",
            }}>
              {riskScore.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Run button */}
      <button
        onClick={handleSubmit}
        disabled={isLoading}
        style={{
          background: isLoading
            ? "#1e3a5f"
            : "linear-gradient(135deg, #3b82f6, #2563eb)",
          color: "white",
          border: "none",
          borderRadius: "10px",
          padding: "14px",
          fontSize: "14px",
          fontWeight: 700,
          cursor: isLoading ? "not-allowed" : "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          opacity: isLoading ? 0.7 : 1,
        }}
      >
        {isLoading ? (
          <>
            <span style={{
              width: "14px", height: "14px",
              border: "2px solid rgba(255,255,255,0.3)",
              borderTopColor: "white",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              display: "inline-block",
            }}/>
            Running Pipeline...
          </>
        ) : (
          <> ▶ Run Pipeline </>
        )}
      </button>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}