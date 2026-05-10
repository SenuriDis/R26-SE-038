const SEV_COLORS = {
  critical: { bg: "#450a0a", color: "#fca5a5", dot: "#ef4444" },
  high:     { bg: "#431407", color: "#fdba74", dot: "#f97316" },
  medium:   { bg: "#422006", color: "#fcd34d", dot: "#f59e0b" },
  low:      { bg: "#1e3a5f", color: "#93c5fd", dot: "#3b82f6" },
  info:     { bg: "#1e293b", color: "#94a3b8", dot: "#6b7280" },
};

function PylintBar({ score }) {
  if (score === null || score === undefined) return null;
  const pct = (score / 10) * 100;
  const color = score >= 7 ? "#10b981" : score >= 4 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <span style={{ fontSize: "12px", color: "#64748b" }}>Pylint</span>
      <div style={{
        flex: 1, height: "6px",
        background: "#2d3748", borderRadius: "3px", overflow: "hidden",
      }}>
        <div style={{
          width: `${pct}%`, height: "100%",
          background: color, borderRadius: "3px",
          transition: "width 0.6s ease",
        }}/>
      </div>
      <span style={{ fontSize: "13px", fontWeight: 700, color }}>{score}/10</span>
    </div>
  );
}

export default function ReviewCard({ review }) {
  return (
    <div style={{
      background: "#1a1f2e",
      border: "1px solid #2d3748",
      borderRadius: "10px",
      marginBottom: "16px",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "14px 18px",
        borderBottom: "1px solid #2d3748",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}>
        <span style={{
          fontFamily: "monospace",
          fontSize: "14px",
          color: "#93c5fd",
          fontWeight: 600,
        }}>
          {review.function_name}()
        </span>
        <PylintBar score={review.pylint_score} />
      </div>

      {/* Summary */}
      <div style={{
        padding: "12px 18px",
        fontSize: "13px",
        color: "#94a3b8",
        lineHeight: 1.6,
        borderBottom: "1px solid #1e293b",
      }}>
        {review.summary}
      </div>

      {/* Findings */}
      {review.findings.length === 0 ? (
        <div style={{ padding: "14px 18px", fontSize: "13px", color: "#4b5563" }}>
          No findings
        </div>
      ) : (
        review.findings.map((f, i) => {
          const sev = SEV_COLORS[f.severity] || SEV_COLORS.info;
          return (
            <div key={i} style={{
              padding: "12px 18px",
              borderBottom: "1px solid #1e293b",
              display: "flex",
              gap: "12px",
            }}>
              <div style={{
                width: "8px", height: "8px",
                borderRadius: "50%",
                background: sev.dot,
                marginTop: "5px",
                flexShrink: 0,
              }}/>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: "6px", marginBottom: "6px", flexWrap: "wrap" }}>
                  <span style={{
                    background: "#1e293b", color: "#94a3b8",
                    fontSize: "11px", padding: "2px 8px", borderRadius: "20px",
                  }}>
                    {f.category}
                  </span>
                  <span style={{
                    background: sev.bg, color: sev.color,
                    fontSize: "11px", fontWeight: 700,
                    padding: "2px 8px", borderRadius: "20px",
                  }}>
                    {f.severity.toUpperCase()}
                  </span>
                  {f.line_number && (
                    <span style={{ fontSize: "11px", color: "#4b5563" }}>
                      Line {f.line_number}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: "13px", color: "#e2e8f0", marginBottom: "4px" }}>
                  {f.description}
                </div>
                <div style={{ fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
                  💡 {f.suggested_fix}
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}