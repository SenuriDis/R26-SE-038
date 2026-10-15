import { ClipboardCheck, FileWarning, FileQuestion, Percent } from "lucide-react";

// Displays the project_summary block from requirement_analysis:
// total functions, documented+implemented, documented but missing,
// implemented but undocumented, and the average coverage score.
function RequirementCoverageCard({ projectSummary }) {
  if (!projectSummary) return null;

  const coveragePercent = Math.round(
    (projectSummary.average_specification_coverage || 0) * 100
  );

  return (
    <div className="mt-8">
      <h3 className="text-2xl font-bold text-slate-800 mb-5">
        Requirement Coverage
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="bg-slate-100 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Documented &amp; Implemented</p>
              <h2 className="text-4xl font-bold mt-3 text-green-600">
                {projectSummary.documented_and_implemented}
              </h2>
            </div>
            <ClipboardCheck className="text-green-600" size={26} />
          </div>
        </div>

        <div className="bg-slate-100 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Documented but Missing</p>
              <h2 className="text-4xl font-bold mt-3 text-red-500">
                {projectSummary.documented_but_missing}
              </h2>
            </div>
            <FileWarning className="text-red-500" size={26} />
          </div>
        </div>

        <div className="bg-slate-100 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Implemented, Undocumented</p>
              <h2 className="text-4xl font-bold mt-3 text-amber-500">
                {projectSummary.implemented_but_undocumented}
              </h2>
            </div>
            <FileQuestion className="text-amber-500" size={26} />
          </div>
        </div>

        <div className="bg-slate-100 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Average Coverage</p>
              <h2 className="text-4xl font-bold mt-3 text-cyan-600">
                {coveragePercent}%
              </h2>
            </div>
            <Percent className="text-cyan-600" size={26} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default RequirementCoverageCard;
