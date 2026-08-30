const steps = [
  { id: "rag",  icon: "🗄️", label: "RAG Indexer" },
  { id: "a1",   icon: "🤖", label: "Agent 1 — Test Generation" },
  { id: "a2",   icon: "🔧", label: "Agent 2 — Validation & Repair" },
  { id: "a3",   icon: "🔍", label: "Agent 3 — Code Review" },
  { id: "out",  icon: "📦", label: "Output" },
];

export default function PipelineFlow({ activeStep }) {
  return (
    <div style={{
      background: "#1a1f2e",
      borderBottom: "1px solid #2d3748",
      padding: "14px 40px",
      display: "flex",
      alignItems: "center",
      gap: "8px",
      overflowX: "auto",
    }}>
      {steps.map((step, i) => {
        const isDone   = activeStep > i;
        const isActive = activeStep === i;

        return (
          <div key={step.id} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: isDone ? "#064e3b" : isActive ? "#1e3a5f" : "#0f1117",
              border: `1px solid ${isDone ? "#10b981" : isActive ? "#3b82f6" : "#2d3748"}`,
              borderRadius: "8px",
              padding: "8px 14px",
              fontSize: "12px",
              color: isDone ? "#6ee7b7" : isActive ? "#93c5fd" : "#64748b",
              whiteSpace: "nowrap",
              transition: "all 0.4s",
              fontWeight: isActive || isDone ? 600 : 400,
            }}>
              <span>{step.icon}</span>
              <span>{step.label}</span>
              {isDone && <span>✓</span>}
            </div>
            {i < steps.length - 1 && (
              <span style={{ color: "#4b5563", fontSize: "16px" }}>→</span>
            )}
          </div>
        );
      })}
    </div>
  );
}