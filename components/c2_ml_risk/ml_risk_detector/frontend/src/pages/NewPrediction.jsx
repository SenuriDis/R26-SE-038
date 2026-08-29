import { useState } from 'react';
import FunctionForm, { emptyFunction, formToPayload } from '../components/FunctionForm';
import ResultCard from '../components/ResultCard';
import { api, historyStore } from '../services/api';
import { useToast } from '../context/ToastContext';

const DEMO = [
  { id: 1, function_name:'process_transaction', file_path:'src/payment.py', start_line:45, end_line:78, cyclomatic_complexity:18, nesting_depth:5, lines_of_code:87, fan_in:3, fan_out:12, num_parameters:4, commit_frequency:23, author_count:4, bug_history:3, days_since_last_change:7, num_return_statements:5, num_exception_handlers:3, num_loops:4, num_conditionals:12, has_recursion:false, dependencies:'validate_input, calculate_tax, update_ledger' },
  { id: 2, function_name:'validate_payment',    file_path:'src/payment.py', start_line:112, end_line:140, cyclomatic_complexity:9, nesting_depth:3, lines_of_code:45, fan_in:8, fan_out:5, num_parameters:3, commit_frequency:12, author_count:2, bug_history:1, days_since_last_change:14, num_return_statements:4, num_exception_handlers:1, num_loops:1, num_conditionals:6, has_recursion:false, dependencies:'check_card, verify_cvv' },
  { id: 3, function_name:'format_receipt',      file_path:'src/output.py',  start_line:34, end_line:52, cyclomatic_complexity:2, nesting_depth:1, lines_of_code:18, fan_in:5, fan_out:1, num_parameters:2, commit_frequency:3, author_count:1, bug_history:0, days_since_last_change:90, num_return_statements:1, num_exception_handlers:0, num_loops:0, num_conditionals:1, has_recursion:false, dependencies:'format_date' },
];

export default function NewPrediction() {
  const toast = useToast();
  const [projectName, setProjectName] = useState('my-project');
  const [functions, setFunctions] = useState([emptyFunction()]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [processingMs, setProcessingMs] = useState(null);

  const addFn    = () => setFunctions(prev => [...prev, emptyFunction()]);
  const removeFn = (id) => setFunctions(prev => prev.filter(f => f.id !== id));
  const updateFn = (id, data) => setFunctions(prev => prev.map(f => f.id === id ? data : f));

  const loadDemo = () => {
    setFunctions(DEMO);
    toast('Demo data loaded — 3 functions ready.', 'success');
  };

  const handleJsonImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const raw  = JSON.parse(ev.target.result);
        const fns  = raw.functions || raw.ranked_functions || (Array.isArray(raw) ? raw : null);
        if (!fns) throw new Error('No "functions" array found.');
        setFunctions(fns.map((f, i) => ({
          ...f, id: i + 1,
          dependencies: Array.isArray(f.dependencies) ? f.dependencies.join(', ') : (f.dependencies || ''),
        })));
        toast(`Imported ${fns.length} function(s).`, 'success');
      } catch (err) {
        toast('Import failed: ' + err.message, 'error');
      }
    };
    reader.readAsText(file);
  };

  const runPrediction = async () => {
    if (functions.length === 0) { toast('Add at least one function.', 'error'); return; }
    setLoading(true);
    try {
      const payload = {
        project_name: projectName,
        functions: functions.map(formToPayload),
      };
      const result = await api.predict(payload);
      setResults(result);
      setProcessingMs(result.processing_time_ms);

      // Save to history
      const ts = new Date().toISOString();
      historyStore.push(result.ranked_functions.map(fn => ({
        timestamp: ts, project: result.project,
        function_name: fn.function_name, file_path: fn.file_path,
        risk_score: fn.risk_score, risk_level: fn.risk_level,
        confidence: fn.confidence, explanation_text: fn.explanation_text,
        top_risk_factors: fn.top_risk_factors,
        recommended_test_depth: fn.recommended_test_depth,
        test_types: fn.test_types, rf_score: fn.rf_score, xgb_score: fn.xgb_score,
      })));
      toast(`Prediction complete — ${result.ranked_functions.length} function(s) analysed.`, 'success');
    } catch (err) {
      toast('Prediction failed: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="main-content">
      <div className="page-subnav">+ NEW RISK PREDICTION</div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Submit Function Metrics</h1>
          <p className="page-subtitle">
            Enter code metrics for one or more functions to receive ML-based defect risk scores,
            SHAP explanations, and a prioritised test plan.
          </p>
        </div>
      </div>

      <div className="two-col-layout">
        {/* LEFT */}
        <div className="col-main">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Function Metrics Input</h2>
              <span className="badge badge-info">Manual Entry</span>
            </div>
            <div className="field-group">
              <label className="field-label">Project Name</label>
              <input className="field-input" value={projectName}
                onChange={e => setProjectName(e.target.value)} placeholder="e.g. payment-service" />
            </div>
            {functions.map((fn, i) => (
              <FunctionForm
                key={fn.id} data={fn} index={i}
                onChange={(updated) => updateFn(fn.id, updated)}
                onRemove={() => removeFn(fn.id)}
              />
            ))}
            <button className="btn-outline add-function-btn" onClick={addFn}>
              + Add Another Function
            </button>
          </div>

          {/* JSON Import */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Import from Component 1 JSON</h2>
              <span className="badge badge-info">JSON Import</span>
            </div>
            <p className="card-desc">Paste the JSON output from Component 1 to auto-populate function metrics.</p>
            <label className="upload-zone">
              <div className="upload-icon">📋</div>
              <p className="upload-title">Click to upload Component 1 JSON output</p>
              <p className="upload-sub">Supports .json files from static analysis pipeline</p>
              <input type="file" accept=".json" style={{ display: 'none' }} onChange={handleJsonImport} />
            </label>
          </div>

          {/* Run */}
          <div className="action-row">
            <button className="btn-primary btn-large" onClick={runPrediction} disabled={loading}>
              {loading ? <><span className="spinner" /> Running...</> : 'Run Risk Prediction'}
            </button>
            <button className="btn-secondary" onClick={loadDemo}>Load Demo Data</button>
          </div>

          {/* Results */}
          {results && (
            <>
              <div className="results-header">
                <h2 className="section-title">Prediction Results</h2>
                <span className="processing-time">Processed in {processingMs?.toFixed(0)} ms</span>
              </div>
              {results.ranked_functions.map((fn, i) => (
                <ResultCard key={i} fn={fn} rank={fn.priority_rank} />
              ))}
            </>
          )}
        </div>

        {/* RIGHT */}
        <div className="col-side">
          <div className="card side-card">
            <h2 className="card-title">Scan Configuration</h2>
            <div className="field-group"><label className="field-label">Analysis Mode</label><div className="config-value accent-bg">ML Ensemble Risk Detection</div></div>
            <div className="field-group"><label className="field-label">Models</label><div className="config-value">Random Forest + XGBoost</div></div>
            <div className="field-group"><label className="field-label">Explainability</label><div className="config-value">SHAP TreeExplainer</div></div>
            <div className="field-group"><label className="field-label">Output Format</label><div className="config-value">Prioritised JSON + HTML Report</div></div>
          </div>

          <div className="card side-card tip-card">
            <h2 className="card-title accent">Pro Tip</h2>
            <p className="info-text">
              Functions with high cyclomatic complexity, frequent commits, and bug history receive
              the highest risk scores. SHAP values explain which metric contributed most.
            </p>
          </div>

          <div className="card side-card">
            <h2 className="card-title">Metric Guide</h2>
            <div className="metric-guide-list">
              {[['Cyclomatic Complexity','high'],['Bug History','high'],['Nesting Depth','med'],['Commit Frequency','med'],['Fan-Out','med'],['Lines of Code','low']].map(([name, level]) => (
                <div className="metric-row" key={name}>
                  <span className="metric-name">{name}</span>
                  <span className={`metric-impact ${level}`}>{level === 'high' ? 'High' : level === 'med' ? 'Med' : 'Low'} Impact</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
