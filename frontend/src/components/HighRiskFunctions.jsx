import { AlertOctagon, ShieldCheck } from "lucide-react";

function HighRiskFunctions({ functions }) {
  return (
    <div className="mt-10">

      <div className="flex items-center gap-3 mb-6">

        <div className="bg-red-100 text-red-600 p-3 rounded-2xl">
          <AlertOctagon size={22} />
        </div>

        <div>
          <h3 className="text-2xl font-bold text-slate-800">
            High-Risk Functions
          </h3>

          <p className="text-slate-500 text-sm mt-1">
            Functions identified with elevated structural or logical risk.
          </p>
        </div>

      </div>

      {functions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {functions.map((func, index) => (
            <div
              key={index}
              className="bg-red-50 border border-red-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition"
            >

              <div className="flex items-center justify-between">

                <div>

                  <p className="text-xs uppercase tracking-wide text-red-500 font-semibold">
                    Risk Function
                  </p>

                  <h4 className="text-lg font-bold text-slate-800 mt-2 break-all">
                    {func}
                  </h4>

                </div>

                <div className="bg-red-100 text-red-600 px-3 py-2 rounded-xl text-sm font-semibold">
                  HIGH
                </div>

              </div>

            </div>
          ))}

        </div>
      ) : (
        <div className="bg-green-50 border border-green-100 rounded-2xl p-6 flex items-center gap-4">

          <div className="bg-green-100 text-green-700 p-3 rounded-2xl">
            <ShieldCheck size={24} />
          </div>

          <div>

            <h4 className="font-semibold text-green-700">
              No High-Risk Functions Detected
            </h4>

            <p className="text-green-600 text-sm mt-1">
              The analyzed source structure appears stable and low risk.
            </p>

          </div>

        </div>
      )}

    </div>
  );
}

export default HighRiskFunctions;