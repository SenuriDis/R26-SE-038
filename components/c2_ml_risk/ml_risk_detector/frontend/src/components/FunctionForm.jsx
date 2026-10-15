const DEFAULTS = {
  function_name: '', file_path: '', start_line: 1, end_line: 50,
  cyclomatic_complexity: 1, nesting_depth: 0, lines_of_code: 10,
  fan_in: 0, fan_out: 0, num_parameters: 0, commit_frequency: 0,
  author_count: 1, bug_history: 0, days_since_last_change: 30,
  num_return_statements: 1, num_exception_handlers: 0,
  num_loops: 0, num_conditionals: 0, has_recursion: false, dependencies: '',
};

export function emptyFunction() { return { ...DEFAULTS, id: Date.now() + Math.random() }; }

function Field({ label, children }) {
  return (
    <div className="field-group">
      <label className="field-label">{label}</label>
      {children}
    </div>
  );
}

export default function FunctionForm({ data, index, onChange, onRemove }) {
  const set = (key, val) => onChange({ ...data, [key]: val });
  const num = (key, e) => set(key, parseInt(e.target.value, 10) || 0);

  return (
    <div className="function-card">
      <div className="function-card-header">
        <span className="function-card-title">Function #{index + 1}</span>
        <button className="btn-danger" onClick={onRemove}>Remove</button>
      </div>

      <div className="metrics-grid">
        <Field label="Function Name">
          <input className="field-input fn-name full-span" placeholder="e.g. process_transaction"
            value={data.function_name} onChange={e => set('function_name', e.target.value)} />
        </Field>
        <Field label="File Path">
          <input className="field-input full-span" placeholder="e.g. src/payment.py"
            value={data.file_path} onChange={e => set('file_path', e.target.value)} />
        </Field>
        <Field label="Start Line">
          <input type="number" className="field-input" min="1" value={data.start_line}
            onChange={e => num('start_line', e)} />
        </Field>
        <Field label="End Line">
          <input type="number" className="field-input" min="1" value={data.end_line}
            onChange={e => num('end_line', e)} />
        </Field>
        <Field label="Cyclomatic Complexity">
          <input type="number" className="field-input" min="1" value={data.cyclomatic_complexity}
            onChange={e => num('cyclomatic_complexity', e)} />
        </Field>
        <Field label="Nesting Depth">
          <input type="number" className="field-input" min="0" value={data.nesting_depth}
            onChange={e => num('nesting_depth', e)} />
        </Field>
        <Field label="Lines of Code">
          <input type="number" className="field-input" min="1" value={data.lines_of_code}
            onChange={e => num('lines_of_code', e)} />
        </Field>
        <Field label="Fan-In">
          <input type="number" className="field-input" min="0" value={data.fan_in}
            onChange={e => num('fan_in', e)} />
        </Field>
        <Field label="Fan-Out">
          <input type="number" className="field-input" min="0" value={data.fan_out}
            onChange={e => num('fan_out', e)} />
        </Field>
        <Field label="Parameters">
          <input type="number" className="field-input" min="0" value={data.num_parameters}
            onChange={e => num('num_parameters', e)} />
        </Field>
        <Field label="Commit Frequency">
          <input type="number" className="field-input" min="0" value={data.commit_frequency}
            onChange={e => num('commit_frequency', e)} />
        </Field>
        <Field label="Author Count">
          <input type="number" className="field-input" min="0" value={data.author_count}
            onChange={e => num('author_count', e)} />
        </Field>
        <Field label="Bug History">
          <input type="number" className="field-input" min="0" value={data.bug_history}
            onChange={e => num('bug_history', e)} />
        </Field>
        <Field label="Days Since Change">
          <input type="number" className="field-input" min="0" value={data.days_since_last_change}
            onChange={e => num('days_since_last_change', e)} />
        </Field>
        <Field label="Return Statements">
          <input type="number" className="field-input" min="0" value={data.num_return_statements}
            onChange={e => num('num_return_statements', e)} />
        </Field>
        <Field label="Exception Handlers">
          <input type="number" className="field-input" min="0" value={data.num_exception_handlers}
            onChange={e => num('num_exception_handlers', e)} />
        </Field>
        <Field label="Loops">
          <input type="number" className="field-input" min="0" value={data.num_loops}
            onChange={e => num('num_loops', e)} />
        </Field>
        <Field label="Conditionals">
          <input type="number" className="field-input" min="0" value={data.num_conditionals}
            onChange={e => num('num_conditionals', e)} />
        </Field>
        <Field label="Has Recursion">
          <select className="field-select" value={String(data.has_recursion)}
            onChange={e => set('has_recursion', e.target.value === 'true')}>
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </Field>
        <Field label="Dependencies (comma-separated)">
          <input className="field-input full-span" placeholder="func_a, func_b"
            value={data.dependencies} onChange={e => set('dependencies', e.target.value)} />
        </Field>
      </div>
    </div>
  );
}

export function formToPayload(data) {
  return {
    ...data,
    dependencies: data.dependencies
      ? data.dependencies.split(',').map(s => s.trim()).filter(Boolean)
      : [],
  };
}
