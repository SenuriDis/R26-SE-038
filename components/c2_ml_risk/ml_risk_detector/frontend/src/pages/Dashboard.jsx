import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import StatCard from '../components/StatCard';
import HistoryItem from '../components/HistoryItem';
import { api, historyStore } from '../services/api';
import { useToast } from '../context/ToastContext';

export default function Dashboard() {
  const toast = useToast();
  const [modelStatus, setModelStatus] = useState('checking');
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.health()
      .then(d => setModelStatus(d.model_loaded ? 'ready' : 'not-loaded'))
      .catch(() => setModelStatus('offline'));
    setHistory(historyStore.get());
  }, []);

  const highs  = history.filter(h => h.risk_level === 'HIGH').length;
  const avg    = history.length
    ? (history.reduce((s, h) => s + h.risk_score, 0) / history.length).toFixed(2)
    : null;
  const latest = history.at(-1);

  const modelSub = { ready: 'API connected', 'not-loaded': 'POST /train to load', offline: 'API not reachable', checking: 'Connecting...' };
  const modelSubClass = modelStatus === 'ready' ? 'model-connected' : '';

  return (
    <main className="main-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">ML Risk Dashboard</h1>
          <p className="page-subtitle">
            Function-level defect risk detection with SHAP-based explanations and test prioritization.
          </p>
        </div>
        <Link to="/predict" className="btn-primary">+ New Risk Prediction</Link>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <StatCard
          label="Total Predictions"
          value={history.length}
          sub={<span className={modelSubClass}>{modelSub[modelStatus]}</span>}
        />
        <StatCard label="High-Risk Functions" value={highs} valueClass="danger" sub="Requires exhaustive testing" />
        <StatCard label="Avg Risk Score"      value={avg}   valueClass="accent" sub="Across all functions" />
        <StatCard
          label="Last Prediction"
          value={latest ? new Date(latest.timestamp).toLocaleString() : '—'}
          valueClass="small"
          sub={latest ? `${latest.function_name} (${latest.risk_level})` : 'No predictions yet'}
        />
      </div>

      {/* Info row */}
      <div className="info-row">
        <div className="info-card">
          <h2 className="info-title">Component 2 Overview</h2>
          <p className="info-text">
            This component receives function-level code metrics from Component 1 (Static Code Analysis),
            applies an ensemble ML model (Random Forest + XGBoost) to predict defect risk, and outputs
            prioritised risk scores with SHAP-based explanations for Component 3 (LLM Test Generation).
          </p>
          <div className="pipeline-chips">
            <span className="chip">Comp 1: Static Analysis</span>
            <span className="chip-arrow">→</span>
            <span className="chip chip-active">Comp 2: ML Risk Detector</span>
            <span className="chip-arrow">→</span>
            <span className="chip">Comp 3: LLM Test Gen</span>
          </div>
        </div>
        <div className="info-card ai-suggestion">
          <h2 className="info-title accent">AI Insight</h2>
          <p className="info-text">
            Submit a batch of functions with code metrics to get instant risk scores, SHAP explanations,
            and an automatically prioritised testing plan.
          </p>
        </div>
      </div>

      {/* Recent predictions */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Recent Predictions</h2>
          <button className="btn-outline" onClick={() => setHistory(historyStore.get())}>Refresh</button>
        </div>
        {history.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <p>No predictions yet. <Link to="/predict">Run your first prediction →</Link></p>
          </div>
        ) : (
          history.slice().reverse().slice(0, 5).map((h, i) => (
            <HistoryItem key={i} item={h} />
          ))
        )}
      </div>
    </main>
  );
}
