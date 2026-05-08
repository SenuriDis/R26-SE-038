import {
  BrainCircuit,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

function Recommendations({ recommendations }) {
  return (
    <div className="mt-10">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">

        <div className="bg-cyan-100 text-cyan-700 p-3 rounded-2xl">
          <BrainCircuit size={22} />
        </div>

        <div>

          <h3 className="text-2xl font-bold text-slate-800">
            Intelligent Testing Recommendations
          </h3>

          <p className="text-slate-500 text-sm mt-1">
            AI-generated testing guidance based on structural analysis and risk patterns.
          </p>

        </div>

      </div>

      {/* Recommendation Cards */}
      <div className="space-y-6">

        {recommendations.length > 0 ? (
          recommendations.map((item, index) => (
            <div
              key={index}
              className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm hover:shadow-md transition"
            >

              {/* Top */}
              <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-5">

                <div className="flex items-center gap-3">

                  <div className="bg-cyan-100 text-cyan-700 p-3 rounded-2xl">
                    <Sparkles size={20} />
                  </div>

                  <div>

                    <p className="text-sm text-slate-500">
                      Suggested Testing Target
                    </p>

                    <h4 className="text-2xl font-bold text-slate-800 mt-1 break-all">
                      {item.function}
                    </h4>

                  </div>

                </div>

                <span
                  className={`px-5 py-2 rounded-full text-sm font-semibold w-fit ${
                    item.risk_level === "High"
                      ? "bg-red-100 text-red-700"
                      : item.risk_level === "Medium"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {item.risk_level} Risk
                </span>

              </div>

              {/* Reason */}
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5">

                <p className="text-sm font-semibold text-slate-700 mb-2">
                  AI Reasoning
                </p>

                <p className="text-slate-600 leading-7">
                  {item.reason}
                </p>

              </div>

              {/* Suggested Focus */}
              <div className="mt-6">

                <div className="flex items-center gap-2 mb-4">

                  <ShieldCheck size={18} className="text-cyan-600" />

                  <p className="font-semibold text-slate-800">
                    Suggested Test Focus Areas
                  </p>

                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

                  {item.suggested_test_focus.map((focus, i) => (
                    <div
                      key={i}
                      className="bg-cyan-50 border border-cyan-100 rounded-2xl px-4 py-3 text-slate-700 text-sm"
                    >
                      • {focus}
                    </div>
                  ))}

                </div>

              </div>

            </div>
          ))
        ) : (
          <div className="bg-green-50 border border-green-100 rounded-3xl p-8 flex items-center gap-5">

            <div className="bg-green-100 text-green-700 p-4 rounded-2xl">
              <ShieldCheck size={28} />
            </div>

            <div>

              <h4 className="text-xl font-bold text-green-700">
                No Intelligent Recommendations Generated
              </h4>

              <p className="text-green-600 mt-2">
                The analyzed source appears structurally stable with low testing risk indicators.
              </p>

            </div>

          </div>
        )}

      </div>

    </div>
  );
}

export default Recommendations;