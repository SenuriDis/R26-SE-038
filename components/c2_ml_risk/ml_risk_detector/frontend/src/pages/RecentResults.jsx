import { useState, useEffect } from 'react';
import HistoryItem from '../components/HistoryItem';
import ResultCard from '../components/ResultCard';
import { historyStore } from '../services/api';

const FILTERS = ['all', 'HIGH', 'MEDIUM', 'LOW'];

export default function RecentResults() {
  const [history, setHistory]   = useState([]);
  const [filter, setFilter]     = useState('all');
  const [selected, setSelected] = useState(null);

  useEffect(() => { setHistory(historyStore.get()); }, []);

  const filtered = filter === 'all' ? history : history.filter(h => h.risk_level === filter);
  const displayed = filtered.slice().reverse();

  return (
    <main className="main-content">
      <div className="page-header">
        <div>
          <h1 className="page-title">Prediction History</h1>
          <p className="page-subtitle">Previously analyzed functions and their ML risk scores.</p>
        </div>
        <button className="btn-secondary" onClick={() => setHistory(historyStore.get())}>
          Refresh History
        </button>
      </div>

      {/* Filters */}
      <div className="filter-row">
        {FILTERS.map(f => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All' : f}
          </button>
        ))}
        {history.length > 0 && (
          <button className="filter-btn" style={{ marginLeft: 'auto', color: 'var(--danger)' }}
            onClick={() => { historyStore.clear(); setHistory([]); }}>
            Clear All
          </button>
        )}
      </div>

      {/* List */}
      {displayed.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>No results for this filter.</p>
        </div>
      ) : (
        displayed.map((h, i) => (
          <HistoryItem key={i} item={h} onClick={setSelected} />
        ))
      )}

      {/* Detail Modal */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {selected.function_name}() — {Math.round(selected.risk_score * 100)}% Risk
              </h2>
              <button className="modal-close" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 16 }}>
                {selected.file_path} · {new Date(selected.timestamp).toLocaleString()}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                {[['Risk Level', selected.risk_level], ['Confidence', `${(selected.confidence*100).toFixed(1)}%`],
                  ['RF Score', (selected.rf_score||0).toFixed(3)], ['XGB Score', (selected.xgb_score||0).toFixed(3)]].map(([l,v]) => (
                  <div className="model-stat" key={l}>
                    <div className="model-stat-label">{l}</div>
                    <div className="model-stat-value">{v}</div>
                  </div>
                ))}
              </div>
              <ResultCard fn={selected} rank={1} />
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
