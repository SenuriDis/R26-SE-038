import {
  FileCode2,
  Activity,
  Layers3,
  GitBranch,
} from "lucide-react";

function ResultSummary({ result }) {
  return (
    <>
      {/* File Info */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 mb-8">

        <p className="text-sm text-slate-500 mb-2">
          Analyzed Source File
        </p>

        <div className="flex items-center gap-3">

          <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
            <FileCode2 size={22} />
          </div>

          <p className="font-semibold text-slate-800 break-all">
            {result.file}
          </p>

        </div>

      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">

        {/* Total Lines */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Total Lines
              </p>

              <h2 className="text-4xl font-bold text-slate-800 mt-3">
                {result.summary.total_lines}
              </h2>

              <p className="text-sm text-slate-400 mt-2">
                Source code size
              </p>

            </div>

            <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
              <FileCode2 size={22} />
            </div>

          </div>

        </div>

        {/* Complexity */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Complexity
              </p>

              <h2 className="text-4xl font-bold text-cyan-600 mt-3">
                {result.summary.file_cyclomatic_complexity}
              </h2>

              <p className="text-sm text-slate-400 mt-2">
                Cyclomatic score
              </p>

            </div>

            <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
              <Activity size={22} />
            </div>

          </div>

        </div>

        {/* Nesting Depth */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Nesting Depth
              </p>

              <h2 className="text-4xl font-bold text-purple-600 mt-3">
                {result.summary.nesting_depth}
              </h2>

              <p className="text-sm text-slate-400 mt-2">
                Structural depth
              </p>

            </div>

            <div className="bg-purple-100 text-purple-700 p-3 rounded-xl">
              <Layers3 size={22} />
            </div>

          </div>

        </div>

        {/* Dependencies */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Dependencies
              </p>

              <h2 className="text-4xl font-bold text-orange-500 mt-3">
                {result.summary.total_dependency_calls}
              </h2>

              <p className="text-sm text-slate-400 mt-2">
                Function relations
              </p>

            </div>

            <div className="bg-orange-100 text-orange-700 p-3 rounded-xl">
              <GitBranch size={22} />
            </div>

          </div>

        </div>

      </div>
    </>
  );
}

export default ResultSummary;