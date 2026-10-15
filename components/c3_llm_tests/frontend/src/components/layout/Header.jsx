export default function Header() {
  return (
    <header style={{
      background: "linear-gradient(135deg, #1a1f2e, #16213e)",
      borderBottom: "1px solid #2d3748",
      padding: "18px 40px",
      display: "flex",
      alignItems: "center",
      gap: "14px",
    }}>
      <span style={{
        background: "#3b82f6",
        color: "white",
        fontSize: "11px",
        fontWeight: 700,
        padding: "4px 10px",
        borderRadius: "20px",
        letterSpacing: "1px",
      }}>
        R26-SE-038
      </span>
      <div>
        <h1 style={{ fontSize: "18px", fontWeight: 700, color: "#f1f5f9" }}>
          Intelligent Software Testing System
        </h1>
        <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "2px" }}>
          LLM + ML Enhanced Automatic Test Case Generation and Code Quality Review
        </p>
      </div>
    </header>
  );
}