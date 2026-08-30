import React from "react";

export default function CoveragePanel({ report }) {
  const cv         = report?.coverage_metrics ?? {};
  const perFn      = report?.perFunction ?? [];
  const overallPct = cv.statement_coverage_pct ?? 0;

  function fnColor(pct) {
    if (pct >= 90) return "var(--clr-green)";
    if (pct >= 70) return "var(--clr-cyan)";
    if (pct >= 50) return "var(--clr-yellow)";
    return "var(--clr-red)";
  }

  return (
    <div className="card section fade-up" style={{ animationDelay: ".26s" }}>
      {/* Header row */}
      <div className="cov-header">
        <div className="section-title" style={{ marginBottom: 0 }}>
          Code Coverage
        </div>
        <div>
          <div className="cov-pct-big">{overallPct}%</div>
          <div className="cov-label">
            {cv.statements_covered ?? 0} / {cv.statements_total ?? 0} statements
          </div>
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="cov-overall-bar">
        <div
          className="cov-overall-bar__fill"
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Per-function table */}
      {perFn.length > 0 ? (
        <div className="table-wrap">
          <table className="fn-table" id="coverage-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Function</th>
                <th>Covered / Total</th>
                <th>Coverage</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {perFn.map((fn, i) => (
                <tr key={i}>
                  <td style={{ color: "var(--clr-dimmer)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
                    {fn.file}
                  </td>
                  <td className="fn-name">{fn.function}</td>
                  <td style={{ color: "var(--clr-muted)", fontSize: 11 }}>
                    {fn.covered} / {fn.total}
                  </td>
                  <td>
                    <div className="fn-mini-bar">
                      <div
                        className="fn-mini-fill"
                        style={{
                          width: `${fn.pct}%`,
                          background: fnColor(fn.pct),
                        }}
                      />
                    </div>
                  </td>
                  <td
                    className="fn-pct"
                    style={{ color: fnColor(fn.pct) }}
                  >
                    {fn.pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty" style={{ paddingTop: 16 }}>
          No per-function data — run tests to populate.
        </div>
      )}
    </div>
  );
}
