import { riskBadge } from './ResultCard';

export default function HistoryItem({ item, onClick }) {
  const scorePct = Math.round((item.risk_score || 0) * 100);
  return (
    <div className="history-item" onClick={() => onClick && onClick(item)}>
      <div>
        <div className="history-fn-name">{item.function_name}()</div>
        <div className="history-fn-meta">
          {new Date(item.timestamp).toLocaleString()} · {item.project || ''}
        </div>
        <div className="history-fn-path">{item.file_path}</div>
      </div>
      <div className="history-right">
        <div className={`history-score ${item.risk_level}`}>{scorePct}%</div>
        <span className={riskBadge(item.risk_level)}>{item.risk_level}</span>
      </div>
    </div>
  );
}
