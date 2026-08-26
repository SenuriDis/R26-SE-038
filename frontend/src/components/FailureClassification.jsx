import React from "react";

export default function FailureClassification({ report }) {
  const failedTests = report?.test_results?.failed_tests ?? [];

  if (failedTests.length === 0) {
    return (
      <div className="card section fade-up" style={{ animationDelay: ".18s" }}>
        <div className="section-title">Failure Classification</div>
        <div style={{ padding: "20px", textAlign: "center", color: "var(--clr-muted)" }}>
          {/* <span style={{ fontSize: "24px", display: "block", marginBottom: "8px" }}>🎉</span> */}
          All tests passed successfully! No failures to classify.
        </div>
      </div>
    );
  }

  function getChipClass(type) {
    const t = type?.toLowerCase() || "";
    if (t.includes("defect")) return "chip chip--failed";
    if (t.includes("environment")) return "chip chip--skip";
    return "chip";
  }

  return (
    <div className="card section fade-up" style={{ animationDelay: ".18s" }}>
      <div className="section-title">Failure Classification</div>
      <div className="table-wrap">
        <table className="test-table">
          <thead>
            <tr>
              <th>Test Name</th>
              <th>Classification</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {failedTests.map((t, i) => {
              const name = t.name ? t.name.split("::").pop() : "Unknown Test";
              return (
                <tr key={i}>
                  <td>
                    <div className="test-name">{name}</div>
                  </td>
                  <td>
                    <span className={getChipClass(t.failure_type)}>
                      {t.failure_type || "Unknown"}
                    </span>
                  </td>
                  <td>
                    <div className="test-reason" style={{ marginTop: 0, whiteSpace: "pre-wrap" }}>
                      {t.message || "No message available"}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
