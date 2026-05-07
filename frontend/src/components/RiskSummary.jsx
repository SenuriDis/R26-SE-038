function RiskSummary({ riskSummary }) {
  return (
    <div className="mt-8">
      <h4 className="text-2xl font-semibold mb-4">Risk Summary</h4>

      <div className="flex flex-wrap gap-4">
        <div className="bg-red-100 text-red-700 px-5 py-3 rounded-xl">
          High: {riskSummary.high}
        </div>

        <div className="bg-yellow-100 text-yellow-700 px-5 py-3 rounded-xl">
          Medium: {riskSummary.medium}
        </div>

        <div className="bg-green-100 text-green-700 px-5 py-3 rounded-xl">
          Low: {riskSummary.low}
        </div>
      </div>
    </div>
  );
}

export default RiskSummary;