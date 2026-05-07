function HighRiskFunctions({ functions }) {
  return (
    <div className="mt-8">
      <h4 className="text-2xl font-semibold mb-4">High Risk Functions</h4>

      {functions.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {functions.map((func, index) => (
            <span
              key={index}
              className="bg-red-50 text-red-700 border border-red-100 px-4 py-2 rounded-full"
            >
              {func}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-slate-500">No high-risk functions detected.</p>
      )}
    </div>
  );
}

export default HighRiskFunctions;