import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';

export default function ModelManagement() {
  const toast = useToast();
  const [health, setHealth]     = useState(null);
  const [info, setInfo]         = useState(null);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState(null);

  const fetchStatus = async () => {
    try {
      const [h, i] = await Promise.all([api.health(), api.modelInfo().catch(() => null)]);
      setHealth(h);
      setInfo(i);
    } catch {
      setHealth({ status: 'error', model_loaded: false });
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  const trainModel = async () => {
    setTraining(true);
    setTrainResult(null);
    try {
      const result = await api.train();
      setTrainResult(result);
      toast(`Model trained! F1: ${result.evaluation?.f1_score?.toFixed(3) ?? '—'}`, 'success');
      fetchStatus();
    } catch (err) {
      toast('Training failed: ' + err.message, 'error');
    } finally {
      setTraining(false);
    }
  };

  const loaded = health?.model_loaded;

  return (
    <main className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Management</h1>
          <p className="page-subtitle">
            Train, evaluate and inspect the ML ensemble used for defect risk detection.
          </p>
        </div>
        <span className={`badge ${loaded ? 'badge-ok' : health ? 'badge-error' : 'badge-loading'}`} style={{ fontSize: 13, padding: '8px 16px' }}>
          {loaded ? 'Model Ready' : health ? 'Not Loaded' : 'Checking...'}
        </span>
      </div>

      {/* Model info */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Model Configuration</h2>
        </div>
        <div className="model-status-grid">
          {[
            ['Ensemble', info?.ensemble ?? 'RF(40%) + XGBoost(50%) + LR(10%)'],
            ['High-Risk Threshold', `≥ ${info?.thresholds?.HIGH ?? 0.65}`],
            ['Medium-Risk Threshold', `≥ ${info?.thresholds?.MEDIUM ?? 0.35}`],
            ['Explainability', 'SHAP TreeExplainer'],
            ['Imbalance Handling', 'SMOTE Oversampling'],
            ['Validation', '5-Fold Cross-Validation'],
          ].map(([label, value]) => (
            <div className="model-stat" key={label}>
              <div className="model-stat-label">{label}</div>
              <div className="model-stat-value">{value}</div>
            </div>
          ))}
        </div>
        <div className="model-action-row">
          <button className="btn-secondary" onClick={trainModel} disabled={training}>
            {training ? <><span className="spinner" /> Training...</> : 'Train / Retrain Model'}
          </button>
          <span className="model-action-hint">POST /train endpoint</span>
        </div>
      </div>

      {/* Training result */}
      {trainResult && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Training Results</h2>
            <span className="badge badge-ok">Complete</span>
          </div>
          <div className="model-status-grid">
            {Object.entries(trainResult.evaluation || {}).map(([k, v]) => (
              <div className="model-stat" key={k}>
                <div className="model-stat-label">{k.replace(/_/g, ' ')}</div>
                <div className="model-stat-value">{Number(v).toFixed(4)}</div>
              </div>
            ))}
          </div>
          <div className="field-group" style={{ marginTop: 12 }}>
            <label className="field-label">Model Path</label>
            <div className="config-value">{trainResult.model_path}</div>
          </div>
        </div>
      )}

      {/* Features */}
      {info?.features && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Feature Set ({info.features.length} features)</h2>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {info.features.map(f => (
              <span className="chip chip-active" key={f}>{f}</span>
            ))}
          </div>
        </div>
      )}

      {/* Metric targets */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Proposal Performance Targets</h2>
        </div>
        <div className="model-status-grid">
          {[['Precision','≥ 0.85'],['Recall','≥ 0.80'],['F1-Score','≥ 0.82'],['ROC-AUC','≥ 0.80']].map(([m,t]) => (
            <div className="model-stat" key={m}>
              <div className="model-stat-label">{m}</div>
              <div className="model-stat-value" style={{ color: 'var(--accent-dark)' }}>{t}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
