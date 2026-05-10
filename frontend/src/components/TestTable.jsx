import React, { useState } from "react";

export default function TestTable({ tests = [] }) {
  const [filter, setFilter] = useState("all");

  const visible = tests.filter(t => {
    if (filter === "all")    return true;
    if (filter === "passed") return t.outcome === "passed";
    if (filter === "failed") return t.outcome !== "passed" && t.outcome !== "skipped";
    if (filter === "skipped") return t.outcome === "skipped";
    return true;
  });

  const counts = {
    all:     tests.length,
    passed:  tests.filter(t => t.outcome === "passed").length,
    failed:  tests.filter(t => t.outcome !== "passed" && t.outcome !== "skipped").length,
    skipped: tests.filter(t => t.outcome === "skipped").length,
  };

  return (
    <div className="card section fade-up" style={{ animationDelay: ".2s" }}>
      <div className="section-title">Test Results</div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {["all", "passed", "failed", "skipped"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "5px 14px",
              borderRadius: 999,
              border: "1px solid",
              borderColor: filter === f ? "var(--clr-violet)" : "var(--clr-border)",
              background:  filter === f ? "rgba(139,92,246,.15)" : "transparent",
              color:       filter === f ? "var(--clr-violet)"    : "var(--clr-muted)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              transition: "all .2s",
            }}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}&nbsp;
            <span style={{ opacity: .7 }}>({counts[f]})</span>
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="empty">No tests match this filter.</div>
      ) : (
        <div className="table-wrap">
          <table className="test-table" id="test-results-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Test Name</th>
                <th>Outcome</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((t, i) => (
                <tr key={t.nodeid || i}>
                  <td style={{ color: "var(--clr-dimmer)", fontSize: 11, width: 36 }}>
                    {i + 1}
                  </td>
                  <td>
                    <div className="test-name">{t.name}</div>
                    {t.reason && (
                      <div className="test-reason">↳ {t.reason}</div>
                    )}
                  </td>
                  <td><OutcomeChip outcome={t.outcome} /></td>
                  <td className="test-dur">
                    {t.duration != null ? `${t.duration} ms` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function OutcomeChip({ outcome }) {
  const o = outcome?.toLowerCase();
  if (o === "passed") return <span className="chip chip--pass">✓ Pass</span>;
  if (o === "skipped") return <span className="chip chip--skip">⊘ Skip</span>;
  return <span className="chip chip--failed">✗ Fail</span>;
}
