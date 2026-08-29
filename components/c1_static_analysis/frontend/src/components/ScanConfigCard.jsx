function ScanConfigCard() {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
        <h3 className="text-xl font-semibold text-slate-800 mb-4">
          Scan Configuration
        </h3>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-slate-500">Target Language</p>
            <div className="mt-1 bg-slate-100 rounded-lg px-4 py-3">
              Python
            </div>
          </div>

          <div>
            <p className="text-sm text-slate-500">Analysis Mode</p>
            <div className="mt-1 bg-cyan-100 text-cyan-700 rounded-lg px-4 py-3">
              Intelligent Static Analysis
            </div>
          </div>

          <div>
            <p className="text-sm text-slate-500">Output Type</p>
            <div className="mt-1 bg-slate-100 rounded-lg px-4 py-3">
              ML-ready + LLM-ready Context
            </div>
          </div>
        </div>
      </div>

      <div className="bg-cyan-50 rounded-2xl p-6 border border-cyan-100">
        <h3 className="text-xl font-semibold text-cyan-700 mb-3">Pro Tip</h3>
        <p className="text-slate-600 text-sm leading-6">
          The system extracts AST-based structural features, detects high-risk
          functions, and generates intelligent testing recommendations for
          LLM-ready software testing workflows.
        </p>
      </div>
    </div>
  );
}

export default ScanConfigCard;