import React from "react";

const GRADE_MAP = {
  A: { color: "var(--grade-a)", label: "Excellent" },
  B: { color: "var(--grade-b)", label: "Good" },
  C: { color: "var(--grade-c)", label: "Acceptable" },
  D: { color: "var(--grade-d)", label: "Needs Improvement" },
};

function parseGradeLetter(gradeStr = "") {
  // e.g. "A — Excellent"
  const letter = gradeStr.trim()[0]?.toUpperCase();
  return GRADE_MAP[letter] ? { letter, ...GRADE_MAP[letter] } : null;
}

const R  = 50;   
const C  = 2 * Math.PI * R;  


/* GradeBadge — SVG ring + grade letter + bar charts for pass rate, coverage & mutation. */
export default function GradeBadge({ report }) {
  const ev       = report?.evaluation_summary ?? {};
  const mt       = report?.mutation_metrics   ?? {};
  const raw      = ev.quality_grade ?? "";
  const info     = parseGradeLetter(raw);

  const passRate  = ev.pass_rate_pct          ?? 0;
  const coverage  = ev.statement_coverage_pct ?? 0;
  const mutation  = ev.mutation_score_pct ?? mt.mutation_score_pct ?? 0;
  const hasMutation = mutation > 0;
  const score     = hasMutation
    ? (passRate + coverage + mutation) / 3
    : (passRate + coverage) / 2;

  const filled = C * (1 - score / 100);

  return (
    <div className="card section fade-up" style={{ animationDelay: ".14s" }}>
      <div className="section-title">Quality Evaluation</div>

      <div className="grade-section">
        {/* SVG Ring */}
        <div className="grade-ring">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle
              className="grade-ring__track"
              cx="60" cy="60" r={R}
            />
            <circle
              className="grade-ring__fill"
              cx="60" cy="60" r={R}
              stroke={info?.color ?? "var(--clr-violet)"}
              strokeDasharray={C}
              strokeDashoffset={info ? filled : C}
            />
          </svg>
          <div
            className="grade-ring__label"
            style={{ color: info?.color ?? "var(--clr-muted)" }}
          >
            {info?.letter ?? "—"}
          </div>
        </div>

        {/* Info + bars */}
        <div className="grade-info">
          <div
            className="grade-title"
            style={{ color: info?.color ?? "var(--clr-text)" }}
          >
            {info ? `Grade ${info.letter} — ${info.label}` : "No data"}
          </div>
          <div className="grade-desc">
            Combined score: <strong>{Math.round(score)}%</strong>
            &nbsp;(pass rate + statement coverage ÷ 2)
          </div>

          <div className="grade-bar">
            <BarRow
              label="Pass Rate"
              pct={passRate}
              color="var(--clr-green)"
            />
            <BarRow
              label="Coverage"
              pct={coverage}
              color="var(--clr-cyan)"
            />
            {hasMutation && (
              <BarRow
                label="Mutation"
                pct={mutation}
                color="var(--clr-violet)"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function BarRow({ label, pct, color }) {
  return (
    <div className="grade-bar__row">
      <span className="grade-bar__name">{label}</span>
      <div className="grade-bar__track">
        <div
          className="grade-bar__fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="grade-bar__pct">{pct}%</span>
    </div>
  );
}
