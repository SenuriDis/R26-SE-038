import React, { useEffect, useRef, useState } from "react";

function useCountUp(target, duration = 900) {
  const [val, setVal] = useState(0);
  const raf = useRef(null);

  useEffect(() => {
    if (target == null) return;
    let start = null;
    const from = 0;
    const to   = parseFloat(target);

    function step(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased    = 1 - Math.pow(1 - progress, 3);
      setVal(parseFloat((from + (to - from) * eased).toFixed(to % 1 === 0 ? 0 : 1)));
      if (progress < 1) raf.current = requestAnimationFrame(step);
    }

    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [target, duration]);

  return val;
}

function StatCard({ value, label, sub, accentColor, showPct }) {
  const animated = useCountUp(value);
  return (
    <div
      className="summary-card"
      style={{ "--card-accent": accentColor }}
    >
      <div
        className="summary-card__value"
        style={{ color: accentColor }}
      >
        {animated}{showPct ? "%" : ""}
      </div>
      <div className="summary-card__label">{label}</div>
      {sub && <div className="summary-card__sub">{sub}</div>}
    </div>
  );
}

/* SummaryCards — six metric cards across the top. */
export default function SummaryCards({ report }) {
  const tr = report?.test_results       ?? {};
  const ev = report?.evaluation_summary ?? {};
  const cv = report?.coverage_metrics   ?? {};
  const mt = report?.mutation_metrics   ?? {};

  return (
    <div className="summary-grid fade-up" style={{ animationDelay: ".08s" }}>
      <StatCard
        value={tr.total ?? 0}
        label="Total Tests"
        accentColor="#1a202c"
      />
      <StatCard
        value={tr.passed ?? 0}
        label="Passed"
        accentColor="#16a34a"
      />
      <StatCard
        value={tr.failed ?? 0}
        label="Failed"
        accentColor="#dc2626"
      />
      <StatCard
        value={ev.pass_rate_pct ?? tr.pass_rate_pct ?? 0}
        label="Pass Rate"
        sub="percentage"
        accentColor="#2563eb"
        showPct
      />
      <StatCard
        value={cv.statement_coverage_pct ?? ev.statement_coverage_pct ?? 0}
        label="Coverage"
        sub="statements"
        accentColor="#0891b2"
        showPct
      />
      <StatCard
        value={ev.mutation_score_pct ?? mt.mutation_score_pct ?? 0}
        label="Mutation Score"
        sub={mt.killed_mutants != null ? `${mt.killed_mutants}/${mt.total_mutants} killed` : undefined}
        accentColor="#7c3aed"
        showPct
      />
    </div>
  );
}
