function ResultSummary({ result }) {
  return (
    <>
      <p className="text-sm text-slate-500 mb-6 break-all">
        <span className="font-semibold text-slate-700">File:</span>{" "}
        {result.file}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-100 rounded-xl p-4">
          <p className="text-sm text-slate-500">Total Lines</p>
          <p className="text-2xl font-bold mt-2">{result.summary.total_lines}</p>
        </div>

        <div className="bg-slate-100 rounded-xl p-4">
          <p className="text-sm text-slate-500">Complexity</p>
          <p className="text-2xl font-bold mt-2">
            {result.summary.file_cyclomatic_complexity}
          </p>
        </div>

        <div className="bg-slate-100 rounded-xl p-4">
          <p className="text-sm text-slate-500">Nesting Depth</p>
          <p className="text-2xl font-bold mt-2">{result.summary.nesting_depth}</p>
        </div>

        <div className="bg-slate-100 rounded-xl p-4">
          <p className="text-sm text-slate-500">Dependencies</p>
          <p className="text-2xl font-bold mt-2">
            {result.summary.total_dependency_calls}
          </p>
        </div>
      </div>
    </>
  );
}

export default ResultSummary;