import React from "react";

export default function Header({ report, running }) {
  const status = running
    ? "RUNNING"
    : report?.execution_status ?? "—";

  const badgeClass =
    running          ? "badge badge--running"
    : status === "PASS" ? "badge badge--pass"
    : status === "FAIL" ? "badge badge--fail"
    : "badge";

  const ts = report?.timestamp
    ? new Date(report.timestamp).toLocaleString()
    : null;

  return (
    <header className="header fade-up">
      <div className="header-brand">
        <div className="header-logo" aria-hidden="true">🧪</div>
        <div>
          <div className="header-title">Intelligent Software Testing System</div>
        </div>
      </div>

      <div className="header-meta">
        {ts && <span className="timestamp">{ts}</span>}
        <span className={badgeClass}>
          <span className="badge-dot" />
          {status}
        </span>
      </div>
    </header>
  );
}
