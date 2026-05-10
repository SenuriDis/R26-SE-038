/* =====================================================
   app.js — ML Risk Detector Frontend
   IT22292872 · W.M.V.S.B Wahundeniya
   ===================================================== */

const API_BASE = 'http://localhost:8000';

// ── Session history (localStorage) ──────────────────
const HISTORY_KEY = 'ml_risk_history';
function getHistory()    { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
function saveHistory(h)  { localStorage.setItem(HISTORY_KEY, JSON.stringify(h)); }

// ── Toast ─────────────────────────────────────────────
let _toastTimer;
function toast(msg, type = '') {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className = type ? `show ${type}` : 'show';
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.className = ''; }, 3200);
}

// ── API helpers ───────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Model status ──────────────────────────────────────
async function checkModelStatus() {
  const badge  = document.getElementById('model-badge');
  const subEl  = document.getElementById('sub-model');
  try {
    const data = await apiFetch('/health');
    if (data.model_loaded) {
      if (badge) { badge.textContent = 'Model Ready'; badge.className = 'badge badge-ok'; }
      if (subEl) { subEl.textContent = 'API connected'; subEl.className = 'stat-sub model-connected'; }
    } else {
      if (badge) { badge.textContent = 'Model Not Loaded'; badge.className = 'badge badge-error'; }
      if (subEl) { subEl.textContent = 'POST /train to load'; subEl.className = 'stat-sub'; }
    }
  } catch {
    if (badge) { badge.textContent = 'API Offline'; badge.className = 'badge badge-error'; }
    if (subEl) { subEl.textContent = 'API not reachable'; subEl.className = 'stat-sub'; }
  }
}

// ── Train model ───────────────────────────────────────
async function trainModel() {
  const btn  = document.getElementById('btn-train');
  const hint = document.getElementById('train-hint');
  if (!btn) return;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Training...';
  try {
    const data = await apiFetch('/train', { method: 'POST' });
    toast(`Model trained! F1: ${data.evaluation?.f1_score?.toFixed(3) ?? '—'}`, 'success');
    if (hint) hint.textContent = 'Training complete ✓';
    checkModelStatus();
  } catch (e) {
    toast('Training failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Train / Retrain Model';
  }
}

// ── Dashboard stats ───────────────────────────────────
function loadDashboardStats() {
  const history = getHistory();
  const total     = document.getElementById('val-total');
  const highRisk  = document.getElementById('val-high-risk');
  const avgScore  = document.getElementById('val-avg-score');
  const latest    = document.getElementById('val-latest');
  const subLatest = document.getElementById('sub-latest');

  if (total)    total.textContent    = history.length;
  const highs   = history.filter(h => h.risk_level === 'HIGH');
  if (highRisk) highRisk.textContent = highs.length;
  if (avgScore) {
    const avg = history.length
      ? (history.reduce((s, h) => s + h.risk_score, 0) / history.length).toFixed(2)
      : '—';
    avgScore.textContent = avg;
  }
  if (history.length > 0 && latest) {
    const last = history[history.length - 1];
    latest.textContent    = new Date(last.timestamp).toLocaleString();
    if (subLatest) subLatest.textContent = `${last.function_name} (${last.risk_level})`;
  }
}

// ── Recent predictions on dashboard ──────────────────
function loadRecentPredictions() {
  const container = document.getElementById('recent-predictions-list');
  if (!container) return;
  const history = getHistory().slice().reverse().slice(0, 5);
  if (history.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p>No predictions yet. <a href="predict.html">Run your first prediction →</a></p></div>`;
    return;
  }
  container.innerHTML = history.map(h => buildHistoryItemHTML(h, false)).join('');
}

// ── Function card (predict page) ──────────────────────
let fnCount = 0;
function addFunctionCard(data = null) {
  fnCount++;
  const id  = `fn-${fnCount}`;
  const container = document.getElementById('functions-container');
  if (!container) return;
  const d = data || {};
  const html = `
    <div class="function-card" id="card-${id}">
      <div class="function-card-header">
        <span class="function-card-title">Function #${fnCount}</span>
        <button class="btn-danger" onclick="removeFunctionCard('${id}')">Remove</button>
      </div>
      <div class="metrics-grid">
        <div class="field-group full-width">
          <label class="field-label">Function Name</label>
          <input type="text" class="field-input fn-name" placeholder="e.g. process_transaction" value="${d.function_name||''}" />
        </div>
        <div class="field-group full-width">
          <label class="field-label">File Path</label>
          <input type="text" class="field-input fn-path" placeholder="e.g. src/payment.py" value="${d.file_path||''}" />
        </div>
        <div class="field-group">
          <label class="field-label">Start Line</label>
          <input type="number" class="field-input fn-start-line" placeholder="1" value="${d.start_line||1}" min="1" />
        </div>
        <div class="field-group">
          <label class="field-label">End Line</label>
          <input type="number" class="field-input fn-end-line" placeholder="50" value="${d.end_line||50}" min="1" />
        </div>
        <div class="field-group">
          <label class="field-label">Cyclomatic Complexity</label>
          <input type="number" class="field-input fn-cc" placeholder="1" value="${d.cyclomatic_complexity||1}" min="1" />
        </div>
        <div class="field-group">
          <label class="field-label">Nesting Depth</label>
          <input type="number" class="field-input fn-nd" placeholder="0" value="${d.nesting_depth||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Lines of Code</label>
          <input type="number" class="field-input fn-loc" placeholder="10" value="${d.lines_of_code||10}" min="1" />
        </div>
        <div class="field-group">
          <label class="field-label">Fan-In</label>
          <input type="number" class="field-input fn-fan-in" placeholder="0" value="${d.fan_in||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Fan-Out</label>
          <input type="number" class="field-input fn-fan-out" placeholder="0" value="${d.fan_out||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Parameters</label>
          <input type="number" class="field-input fn-params" placeholder="0" value="${d.num_parameters||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Commit Frequency</label>
          <input type="number" class="field-input fn-commits" placeholder="0" value="${d.commit_frequency||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Author Count</label>
          <input type="number" class="field-input fn-authors" placeholder="1" value="${d.author_count||1}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Bug History</label>
          <input type="number" class="field-input fn-bugs" placeholder="0" value="${d.bug_history||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Days Since Change</label>
          <input type="number" class="field-input fn-days" placeholder="30" value="${d.days_since_last_change||30}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Return Statements</label>
          <input type="number" class="field-input fn-returns" placeholder="1" value="${d.num_return_statements||1}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Exception Handlers</label>
          <input type="number" class="field-input fn-exc" placeholder="0" value="${d.num_exception_handlers||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Loops</label>
          <input type="number" class="field-input fn-loops" placeholder="0" value="${d.num_loops||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Conditionals</label>
          <input type="number" class="field-input fn-conds" placeholder="0" value="${d.num_conditionals||0}" min="0" />
        </div>
        <div class="field-group">
          <label class="field-label">Has Recursion</label>
          <select class="field-select fn-recursion">
            <option value="false" ${!d.has_recursion?'selected':''}>No</option>
            <option value="true"  ${d.has_recursion?'selected':''}>Yes</option>
          </select>
        </div>
        <div class="field-group full-width">
          <label class="field-label">Dependencies (comma-separated)</label>
          <input type="text" class="field-input fn-deps" placeholder="func_a, func_b, func_c" value="${(d.dependencies||[]).join(', ')}" />
        </div>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
}

function removeFunctionCard(id) {
  const card = document.getElementById('card-' + id);
  if (card) card.remove();
}

function readFunctionCard(card) {
  const g = (cls) => card.querySelector('.' + cls);
  const n = (cls) => parseInt(g(cls)?.value || '0', 10);
  const deps = g('fn-deps')?.value?.split(',').map(s => s.trim()).filter(Boolean) || [];
  return {
    function_name:         g('fn-name')?.value?.trim() || 'unnamed',
    file_path:             g('fn-path')?.value?.trim() || 'unknown.py',
    start_line:            n('fn-start-line') || 1,
    end_line:              n('fn-end-line') || 1,
    cyclomatic_complexity: n('fn-cc') || 1,
    nesting_depth:         n('fn-nd'),
    lines_of_code:         n('fn-loc') || 1,
    fan_in:                n('fn-fan-in'),
    fan_out:               n('fn-fan-out'),
    num_parameters:        n('fn-params'),
    commit_frequency:      n('fn-commits'),
    author_count:          n('fn-authors') || 1,
    bug_history:           n('fn-bugs'),
    days_since_last_change:n('fn-days') || 999,
    num_return_statements: n('fn-returns'),
    num_exception_handlers:n('fn-exc'),
    num_loops:             n('fn-loops'),
    num_conditionals:      n('fn-conds'),
    has_recursion:         g('fn-recursion')?.value === 'true',
    dependencies:          deps,
  };
}

// ── Run prediction ────────────────────────────────────
async function runPrediction() {
  const btn       = document.getElementById('btn-run-prediction');
  const btnText   = document.getElementById('btn-predict-text');
  const projectName = document.getElementById('project-name')?.value?.trim() || 'my-project';
  const cards     = document.querySelectorAll('.function-card');

  if (cards.length === 0) { toast('Add at least one function.', 'error'); return; }

  const functions = Array.from(cards).map(readFunctionCard);

  btn.disabled = true;
  if (btnText) btnText.innerHTML = '<span class="spinner"></span>Running...';

  try {
    const result = await apiFetch('/predict', {
      method: 'POST',
      body: JSON.stringify({ project_name: projectName, functions }),
    });
    displayResults(result);

    // Save each function to history
    const history = getHistory();
    const ts = new Date().toISOString();
    result.ranked_functions.forEach(fn => {
      history.push({
        timestamp:     ts,
        project:       result.project,
        function_name: fn.function_name,
        file_path:     fn.file_path,
        risk_score:    fn.risk_score,
        risk_level:    fn.risk_level,
        confidence:    fn.confidence,
        explanation_text: fn.explanation_text,
        top_risk_factors: fn.top_risk_factors,
        recommended_test_depth: fn.recommended_test_depth,
        test_types:    fn.test_types,
        rf_score:      fn.rf_score,
        xgb_score:     fn.xgb_score,
      });
    });
    saveHistory(history);
    toast(`Prediction complete — ${result.ranked_functions.length} function(s) analysed.`, 'success');

  } catch (e) {
    toast('Prediction failed: ' + e.message, 'error');
    document.getElementById('results-section')?.classList.add('hidden');
  } finally {
    btn.disabled = false;
    if (btnText) btnText.textContent = 'Run Risk Prediction';
  }
}

function displayResults(result) {
  const section   = document.getElementById('results-section');
  const container = document.getElementById('results-container');
  const timeEl    = document.getElementById('processing-time');

  if (!section || !container) return;
  section.classList.remove('hidden');

  if (timeEl) timeEl.textContent = `Processed in ${result.processing_time_ms?.toFixed(0)} ms`;

  container.innerHTML = result.ranked_functions.map(fn => `
    <div class="result-card risk-${fn.risk_level}">
      <div class="result-fn-header">
        <div>
          <div class="result-fn-name">#${fn.priority_rank} ${fn.function_name}()</div>
          <div class="result-fn-path">${fn.file_path} · L${fn.start_line}–${fn.end_line}</div>
        </div>
        <div class="result-score-box">
          <div class="result-score ${fn.risk_level}">${(fn.risk_score * 100).toFixed(0)}%</div>
          <div class="result-conf">Confidence ${(fn.confidence * 100).toFixed(0)}%</div>
          <span class="badge badge-${fn.risk_level.toLowerCase()}">${fn.risk_level} RISK</span>
        </div>
      </div>

      <div class="shap-bar-list">
        ${(fn.top_risk_factors || []).slice(0, 5).map(f => {
          const pct = Math.min(Math.abs(f.contribution) * 300, 100);
          const neg = f.contribution < 0;
          return `<div class="shap-row">
            <span class="shap-feature">${f.feature}</span>
            <div class="shap-bar-wrap"><div class="shap-bar ${neg?'neg':''}" style="width:${pct}%"></div></div>
            <span class="shap-val">${f.contribution > 0 ? '+' : ''}${f.contribution.toFixed(3)}</span>
          </div>`;
        }).join('')}
      </div>

      <div class="result-explanation">${fn.explanation_text}</div>

      <div class="result-test-depth"><strong>Test Depth:</strong> ${fn.recommended_test_depth}</div>
      <div class="result-test-types">
        ${(fn.test_types || []).map(t => `<span class="test-type-chip">${t}</span>`).join('')}
      </div>
    </div>`).join('');

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Demo data ─────────────────────────────────────────
function loadDemoData() {
  const container = document.getElementById('functions-container');
  if (!container) return;
  container.innerHTML = '';
  fnCount = 0;
  const demos = [
    { function_name:'process_transaction', file_path:'src/payment.py', start_line:45, end_line:78, cyclomatic_complexity:18, nesting_depth:5, lines_of_code:87, fan_in:3, fan_out:12, num_parameters:4, commit_frequency:23, author_count:4, bug_history:3, days_since_last_change:7, num_return_statements:5, num_exception_handlers:3, num_loops:4, num_conditionals:12, has_recursion:false, dependencies:['validate_input','calculate_tax','update_ledger'] },
    { function_name:'validate_payment', file_path:'src/payment.py', start_line:112, end_line:140, cyclomatic_complexity:9, nesting_depth:3, lines_of_code:45, fan_in:8, fan_out:5, num_parameters:3, commit_frequency:12, author_count:2, bug_history:1, days_since_last_change:14, num_return_statements:4, num_exception_handlers:1, num_loops:1, num_conditionals:6, has_recursion:false, dependencies:['check_card','verify_cvv'] },
    { function_name:'format_receipt', file_path:'src/output.py', start_line:34, end_line:52, cyclomatic_complexity:2, nesting_depth:1, lines_of_code:18, fan_in:5, fan_out:1, num_parameters:2, commit_frequency:3, author_count:1, bug_history:0, days_since_last_change:90, num_return_statements:1, num_exception_handlers:0, num_loops:0, num_conditionals:1, has_recursion:false, dependencies:['format_date'] },
  ];
  demos.forEach(d => addFunctionCard(d));
  toast('Demo data loaded — 3 functions ready.', 'success');
}

// ── JSON import ───────────────────────────────────────
function handleJsonImport(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      const fns  = data.functions || data.ranked_functions || (Array.isArray(data) ? data : null);
      if (!fns) throw new Error('No "functions" array found in JSON.');
      document.getElementById('functions-container').innerHTML = '';
      fnCount = 0;
      fns.forEach(f => addFunctionCard(f));
      toast(`Imported ${fns.length} function(s) from JSON.`, 'success');
    } catch (err) {
      toast('Import failed: ' + err.message, 'error');
    }
  };
  reader.readAsText(file);
}

// ── History page ──────────────────────────────────────
let _currentFilter = 'all';

function filterHistory(level) {
  _currentFilter = level;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('filter-' + level.toLowerCase());
  if (btn) btn.classList.add('active');
  renderHistoryList();
}

function loadHistoryPage() {
  renderHistoryList();
}

function renderHistoryList() {
  const container = document.getElementById('history-list');
  if (!container) return;
  let history = getHistory().slice().reverse();
  if (_currentFilter !== 'all') history = history.filter(h => h.risk_level === _currentFilter);

  if (history.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">📊</div><p>No results for this filter. <a href="predict.html">Run a prediction →</a></p></div>`;
    return;
  }
  container.innerHTML = history.map(h => buildHistoryItemHTML(h, true)).join('');
}

function buildHistoryItemHTML(h, clickable) {
  const ts     = new Date(h.timestamp).toLocaleString();
  const score  = (h.risk_score * 100).toFixed(0);
  const click  = clickable ? `onclick="openHistoryDetail(${JSON.stringify(h).replace(/"/g, '&quot;')})"` : '';
  return `
    <div class="history-item" ${click}>
      <div>
        <div class="history-fn-name">${h.function_name}()</div>
        <div class="history-fn-meta">${ts} · ${h.project || ''}</div>
        <div class="history-fn-path">${h.file_path || ''}</div>
      </div>
      <div class="history-right">
        <div class="history-score ${h.risk_level}">${score}%</div>
        <span class="badge badge-${(h.risk_level||'low').toLowerCase()}">${h.risk_level}</span>
      </div>
    </div>`;
}

function openHistoryDetail(h) {
  const modal  = document.getElementById('detail-modal');
  const title  = document.getElementById('modal-fn-name');
  const body   = document.getElementById('modal-body');
  if (!modal) return;

  if (title) title.textContent = `${h.function_name}() — ${(h.risk_score*100).toFixed(0)}% Risk`;
  if (body) {
    body.innerHTML = `
      <p style="color:var(--text-muted);font-size:12px;margin-bottom:16px;">${h.file_path} · ${new Date(h.timestamp).toLocaleString()}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
        <div class="model-stat"><div class="model-stat-label">Risk Level</div><div class="model-stat-value">${h.risk_level}</div></div>
        <div class="model-stat"><div class="model-stat-label">Confidence</div><div class="model-stat-value">${(h.confidence*100).toFixed(1)}%</div></div>
        <div class="model-stat"><div class="model-stat-label">RF Score</div><div class="model-stat-value">${(h.rf_score||0).toFixed(3)}</div></div>
        <div class="model-stat"><div class="model-stat-label">XGB Score</div><div class="model-stat-value">${(h.xgb_score||0).toFixed(3)}</div></div>
      </div>
      <div class="result-explanation">${h.explanation_text || '—'}</div>
      <div style="margin-top:12px;">
        <strong style="font-size:13px;">Top SHAP Factors</strong>
        <div class="shap-bar-list" style="margin-top:8px;">
          ${(h.top_risk_factors||[]).slice(0,5).map(f => {
            const pct = Math.min(Math.abs(f.contribution)*300, 100);
            return `<div class="shap-row">
              <span class="shap-feature">${f.feature}</span>
              <div class="shap-bar-wrap"><div class="shap-bar" style="width:${pct}%"></div></div>
              <span class="shap-val">${f.contribution>0?'+':''}${f.contribution.toFixed(3)}</span>
            </div>`;
          }).join('')}
        </div>
      </div>
      <div style="margin-top:14px;">
        <strong style="font-size:13px;">Test Depth:</strong> <span style="color:var(--text-muted)">${h.recommended_test_depth||'—'}</span>
      </div>
      <div class="result-test-types" style="margin-top:8px;">
        ${(h.test_types||[]).map(t => `<span class="test-type-chip">${t}</span>`).join('')}
      </div>`;
  }
  modal.classList.remove('hidden');
}

function closeModal() {
  const modal = document.getElementById('detail-modal');
  if (modal) modal.classList.add('hidden');
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.id === 'detail-modal') closeModal();
});
