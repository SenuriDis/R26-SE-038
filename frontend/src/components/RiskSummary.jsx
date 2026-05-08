import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

function RiskSummary({ riskSummary }) {
  return (
    <div className="mt-10">

      <div className="flex items-center gap-3 mb-6">

        <div className="bg-red-100 text-red-600 p-3 rounded-2xl">
          <AlertTriangle size={22} />
        </div>

        <div>
          <h3 className="text-2xl font-bold text-slate-800">
            Risk Summary
          </h3>

          <p className="text-slate-500 text-sm mt-1">
            Structural risk distribution detected from source analysis.
          </p>
        </div>

      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

        {/* High Risk */}
        <div className="bg-red-50 border border-red-100 rounded-2xl p-6 shadow-sm">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-red-500 font-medium">
                High Risk
              </p>

              <h2 className="text-5xl font-bold text-red-600 mt-3">
                {riskSummary.high}
              </h2>

              <p className="text-sm text-red-400 mt-3">
                Immediate testing priority
              </p>

            </div>

            <div className="bg-red-100 text-red-600 p-4 rounded-2xl">
              <ShieldAlert size={26} />
            </div>

          </div>

        </div>

        {/* Medium Risk */}
        <div className="bg-yellow-50 border border-yellow-100 rounded-2xl p-6 shadow-sm">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-yellow-600 font-medium">
                Medium Risk
              </p>

              <h2 className="text-5xl font-bold text-yellow-600 mt-3">
                {riskSummary.medium}
              </h2>

              <p className="text-sm text-yellow-500 mt-3">
                Requires monitoring
              </p>

            </div>

            <div className="bg-yellow-100 text-yellow-700 p-4 rounded-2xl">
              <AlertTriangle size={26} />
            </div>

          </div>

        </div>

        {/* Low Risk */}
        <div className="bg-green-50 border border-green-100 rounded-2xl p-6 shadow-sm">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-green-600 font-medium">
                Low Risk
              </p>

              <h2 className="text-5xl font-bold text-green-600 mt-3">
                {riskSummary.low}
              </h2>

              <p className="text-sm text-green-500 mt-3">
                Stable structural logic
              </p>

            </div>

            <div className="bg-green-100 text-green-700 p-4 rounded-2xl">
              <ShieldCheck size={26} />
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}

export default RiskSummary;