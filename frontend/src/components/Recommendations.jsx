function Recommendations({ recommendations }) {
  return (
    <div className="mt-10">
      <h4 className="text-2xl font-semibold mb-6">
        Intelligent Testing Recommendations
      </h4>

      <div className="space-y-5">
        {recommendations.length > 0 ? (
          recommendations.map((item, index) => (
            <div
              key={index}
              className="bg-slate-50 border border-slate-200 rounded-2xl p-5"
            >
              <div className="flex justify-between items-center mb-3">
                <h5 className="text-xl font-semibold text-slate-800">
                  {item.function}
                </h5>

                <span
                  className={`px-4 py-1 rounded-full text-sm ${
                    item.risk_level === "High"
                      ? "bg-red-100 text-red-700"
                      : item.risk_level === "Medium"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {item.risk_level}
                </span>
              </div>

              <p className="text-slate-600">{item.reason}</p>

              <div className="mt-4">
                <p className="font-semibold text-slate-700 mb-2">
                  Suggested Test Focus
                </p>

                <ul className="list-disc ml-6 text-slate-600 space-y-1">
                  {item.suggested_test_focus.map((focus, i) => (
                    <li key={i}>{focus}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))
        ) : (
          <p className="text-slate-500">
            No intelligent testing recommendations available.
          </p>
        )}
      </div>
    </div>
  );
}

export default Recommendations;