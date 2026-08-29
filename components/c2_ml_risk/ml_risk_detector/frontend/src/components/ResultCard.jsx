export function riskBadge(level) {
  const map = { HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' };
  return `badge ${map[level] || 'badge-info'}`;
}

export default function ResultCard({ fn, rank }) {
  const scorePct = Math.round((fn.risk_score || 0) * 100);
  return (
    <div className={`result-card risk-${fn.risk_level}`}>
      <div className="result-fn-header">
        <div>
          <div className="result-fn-name">#{rank ?? fn.priority_rank} {fn.function_name}()</div>
          <div className="result-fn-path">
            {fn.file_path} · L{fn.start_line}–{fn.end_line}
          </div>
        </div>
        <div className="result-score-box">
          <div className={`result-score ${fn.risk_level}`}>{scorePct}%</div>
          <div className="result-conf">Confidence {Math.round((fn.confidence || 0) * 100)}%</div>
          <span className={riskBadge(fn.risk_level)}>{fn.risk_level} RISK</span>
        </div>
      </div>

      {/* SHAP bars */}
      <div className="shap-bar-list">
        {(fn.top_risk_factors || []).slice(0, 5).map((f, i) => {
          const pct = Math.min(Math.abs(f.contribution) * 300, 100);
          return (
            <div className="shap-row" key={i}>
              <span className="shap-feature">{f.feature}</span>
              <div className="shap-bar-wrap">
                <div
                  className={`shap-bar ${f.contribution < 0 ? 'neg' : ''}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="shap-val">
                {f.contribution > 0 ? '+' : ''}{f.contribution.toFixed(3)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="result-explanation">{fn.explanation_text}</div>

      <div className="result-test-depth">
        <strong>Test Depth:</strong> {fn.recommended_test_depth}
      </div>
      <div className="result-test-types">
        {(fn.test_types || []).map(t => (
          <span className="test-type-chip" key={t}>{t}</span>
        ))}
      </div>
    </div>
  );
}
