import { AlertTriangle, ShieldCheck } from "lucide-react";

const GAP_LABELS = {
  missing_function: "Function not implemented",
  missing_input_validation: "Missing input validation",
  missing_exception_handling: "Missing exception handling",
  missing_output_definition: "Missing output definition",
  missing_requirement_coverage: "No requirement documented",
};

// For each function, lists which gap_analysis flags are true.
// Functions with zero gaps are omitted -- this panel is specifically
// "what needs attention", not a full listing of every function.
function GapAnalysisPanel({ functions }) {
  if (!functions || functions.length === 0) return null;

  const flaggedFunctions = functions
    .map((fn) => {
      const gaps = Object.entries(fn.gap_analysis || {})
        .filter(([, isMissing]) => isMissing)
        .map(([key]) => GAP_LABELS[key] || key);

      return { function_name: fn.function_name, gaps };
    })
    .filter((fn) => fn.gaps.length > 0);

  return (
    <div className="mt-8">
      <h3 className="text-2xl font-bold text-slate-800 mb-5">
        Gap Analysis
      </h3>

      {flaggedFunctions.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-3xl p-6 flex items-center gap-3">
          <ShieldCheck className="text-green-600" size={22} />
          <p className="text-green-700 font-medium">
            No specification gaps detected across analyzed functions.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {flaggedFunctions.map((fn) => (
            <div
              key={fn.function_name}
              className="bg-red-50 border border-red-200 rounded-3xl p-6"
            >
              <p className="font-mono font-semibold text-slate-800">
                {fn.function_name}
              </p>

              <ul className="mt-3 space-y-2">
                {fn.gaps.map((gapLabel) => (
                  <li
                    key={gapLabel}
                    className="flex items-center gap-2 text-sm text-red-700"
                  >
                    <AlertTriangle size={15} />
                    {gapLabel}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GapAnalysisPanel;
