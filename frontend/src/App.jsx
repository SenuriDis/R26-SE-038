import React, { useCallback, useEffect, useState } from "react";
import Header       from "./components/Header.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import GradeBadge   from "./components/GradeBadge.jsx";
import RunButton    from "./components/RunButton.jsx";
import TestTable    from "./components/TestTable.jsx";
import CoveragePanel from "./components/CoveragePanel.jsx";

export default function App() {
  const [report,   setReport]   = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [running,  setRunning]  = useState(false);
  const [logLines, setLogLines] = useState([]);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      const res  = await fetch("/api/report");
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setReport(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  return (
    <main className="page">
      {/* Header */}
      <Header report={report} running={running} />

      {/* Loading */}
      {loading && (
        <div className="empty">
          <div className="spinner" />
          Loading report data…
        </div>
      )}

      {error && !loading && (
        <div
          className="card section fade-up"
          style={{
            borderColor: "rgba(248,113,113,.3)",
            background:  "rgba(248,113,113,.06)",
            textAlign: "center",
            color: "var(--clr-red)",
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 8 }}>⚠️</div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Could not load report</div>
          <div style={{ fontSize: 12, color: "var(--clr-muted)", marginBottom: 16 }}>
            {error}
          </div>
          <div style={{ fontSize: 12, color: "var(--clr-muted)" }}>
            Make sure <code style={{ fontFamily: "var(--font-mono)" }}>node server.js</code>
            &nbsp;is running on port 3001.
          </div>
        </div>
      )}

      {!loading && (
        <RunButton
          running={running}
          setRunning={setRunning}
          logLines={logLines}
          setLogLines={setLogLines}
          onComplete={fetchReport}
        />
      )}

      {/* Dashboard content */}
      {report && !loading && (
        <>
          <SummaryCards report={report} />

          <div className="two-col">
            <GradeBadge    report={report} />
            <CoveragePanel report={report} />
          </div>

          <TestTable tests={report.tests ?? []} />
        </>
      )}
    </main>
  );
}
