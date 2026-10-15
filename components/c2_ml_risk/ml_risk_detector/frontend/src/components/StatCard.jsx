export default function StatCard({ label, value, sub, valueClass = '' }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${valueClass}`}>{value ?? '—'}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  );
}
