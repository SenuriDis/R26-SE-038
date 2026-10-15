const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health:    ()       => apiFetch('/health'),
  modelInfo: ()       => apiFetch('/model/info'),
  train:     ()       => apiFetch('/train', { method: 'POST' }),
  predict:   (body)   => apiFetch('/predict', { method: 'POST', body: JSON.stringify(body) }),
};

// ── LocalStorage history ──────────────────────────────
const HISTORY_KEY = 'ml_risk_history';
export const historyStore = {
  get:   ()    => JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'),
  save:  (arr) => localStorage.setItem(HISTORY_KEY, JSON.stringify(arr)),
  push:  (items) => {
    const h = historyStore.get();
    items.forEach(item => h.push(item));
    historyStore.save(h);
  },
  clear: ()    => localStorage.removeItem(HISTORY_KEY),
};
