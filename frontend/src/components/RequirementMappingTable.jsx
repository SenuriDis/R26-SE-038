const STATUS_STYLES = {
  documented_implemented: {
    label: "Implemented",
    className: "bg-green-100 text-green-700",
  },
  documented_missing: {
    label: "Missing",
    className: "bg-red-100 text-red-700",
  },
  implemented_undocumented: {
    label: "Undocumented",
    className: "bg-amber-100 text-amber-700",
  },
};

// Renders one row per function from requirement_analysis.functions,
// showing its mapping status and specification coverage score.
function RequirementMappingTable({ functions }) {
  if (!functions || functions.length === 0) return null;

  return (
    <div className="mt-8">
      <h3 className="text-2xl font-bold text-slate-800 mb-5">
        Requirement Mapping
      </h3>

      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">
                Function
              </th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">
                Status
              </th>
              <th className="px-6 py-4 text-sm font-semibold text-slate-600">
                Coverage
              </th>
            </tr>
          </thead>

          <tbody>
            {functions.map((fn) => {
              const style =
                STATUS_STYLES[fn.mapping_status] || {
                  label: fn.mapping_status,
                  className: "bg-slate-100 text-slate-600",
                };

              const coveragePercent = Math.round(
                (fn.specification_metrics?.specification_coverage_score || 0) * 100
              );

              return (
                <tr key={fn.function_name} className="border-t border-slate-100">
                  <td className="px-6 py-4 font-mono text-sm text-slate-800">
                    {fn.function_name}
                  </td>

                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${style.className}`}
                    >
                      {style.label}
                    </span>
                  </td>

                  <td className="px-6 py-4 text-sm text-slate-700">
                    {coveragePercent}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RequirementMappingTable;
