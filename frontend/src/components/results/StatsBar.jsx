export default function StatsBar({ data }) {
  const pct = (data.success_rate * 100).toFixed(0);

  const stats = [
    { label: "Success Rate",   value: `${pct}%`,
      color: pct == 100 ? "#10b981" : "#f59e0b" },
    { label: "Tests Generated", value: data.segments_with_valid_tests },
    { label: "Segments",        value: data.segments_processed },
    { label: "Run ID",          value: data.run_id,
      small: true },
  ];

  return (
    <div style={{ display: "flex", gap: "14px", marginBottom: "24px", flexWrap: "wrap" }}>
      {stats.map((s, i) => (
        <div key={i} style={{
          background: "#1a1f2e",
          border: "1px solid #2d3748",
          borderRadius: "10px",
          padding: "14px 20px",
          minWidth: "110px",
        }}>
          <div style={{
            fontSize: "11px", color: "#64748b",
            textTransform: "uppercase", letterSpacing: "1px",
          }}>
            {s.label}
          </div>
          <div style={{
            fontSize: s.small ? "14px" : "24px",
            fontWeight: 700,
            color: s.color || "#f1f5f9",
            marginTop: "4px",
          }}>
            {s.value}
          </div>
        </div>
      ))}
    </div>
  );
}