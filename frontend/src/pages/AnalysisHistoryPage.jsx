import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import ResultSummary from "../components/ResultSummary";
import RiskSummary from "../components/RiskSummary";
import HighRiskFunctions from "../components/HighRiskFunctions";
import Recommendations from "../components/Recommendations";
import { getAnalysisHistory } from "../services/api";

function AnalysisHistoryPage() {
  const [history, setHistory] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [folderResults, setFolderResults] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getAnalysisHistory();
      setHistory(data);
    } catch (error) {
      console.error(error);
      alert("Failed to load analysis history");
    }
  };

  const getFileName = (filePath) => {
    return filePath.split("\\").pop().split("/").pop();
  };

  const openReport = (item) => {
    setSelectedReport(item);

    if (item.results && item.results.length > 0) {
      setFolderResults(item.results);
      setSelectedResult(item.results[0]);
    } else if (item.result) {
      setFolderResults([]);
      setSelectedResult(item.result);
    } else {
      setFolderResults([]);
      setSelectedResult(null);
    }
  };

  const totalHighRiskFunctions = folderResults.reduce(
    (acc, item) => acc + item.high_risk_functions.length,
    0
  );

  const averageComplexity =
    folderResults.length > 0
      ? (
          folderResults.reduce(
            (acc, item) => acc + item.summary.file_cyclomatic_complexity,
            0
          ) / folderResults.length
        ).toFixed(1)
      : 0;

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />

      <div className="max-w-7xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800">
            Recent Analysis Results
          </h1>

          <p className="text-slate-500 mt-2">
            View saved analysis reports stored in MongoDB Atlas and reopen
            previous file or folder analysis results.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-2xl font-semibold text-slate-800">
                Saved Reports
              </h2>

              <button
                onClick={loadHistory}
                className="bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg text-sm"
              >
                Refresh
              </button>
            </div>

            {history.length > 0 ? (
              <div className="space-y-4 max-h-[650px] overflow-y-auto pr-2">
                {history.map((item) => (
                  <div
                    key={item._id}
                    onClick={() => openReport(item)}
                    className={`border rounded-xl p-4 cursor-pointer transition ${
                      selectedReport?._id === item._id
                        ? "bg-cyan-50 border-cyan-300"
                        : "bg-slate-50 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    <p className="font-semibold text-slate-800">
                      {item.type.replaceAll("_", " ").toUpperCase()}
                    </p>

                    <p className="text-sm text-slate-500 mt-1">
                      {new Date(item.created_at).toLocaleString()}
                    </p>

                    {item.input_path && (
                      <p className="text-xs text-slate-500 mt-2 break-all">
                        Path: {item.input_path}
                      </p>
                    )}

                    {item.file_name && (
                      <p className="text-xs text-slate-500 mt-2">
                        File: {item.file_name}
                      </p>
                    )}

                    <span className="inline-block mt-3 bg-cyan-100 text-cyan-700 px-3 py-1 rounded-full text-xs">
                      Click to open
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-500">
                No saved reports found.
              </p>
            )}
          </div>

          <div className="lg:col-span-2">
            {!selectedResult && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 text-center">
                <p className="text-slate-500">
                  Select a saved report to view analysis details.
                </p>
              </div>
            )}

            {folderResults.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm p-6 border border-slate-200 mb-6">
                <h3 className="text-2xl font-bold text-slate-800 mb-6">
                  Folder Report Overview
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <div className="bg-slate-100 rounded-xl p-4">
                    <p className="text-sm text-slate-500">Files Analyzed</p>
                    <p className="text-3xl font-bold mt-2">
                      {folderResults.length}
                    </p>
                  </div>

                  <div className="bg-slate-100 rounded-xl p-4">
                    <p className="text-sm text-slate-500">
                      Total High-Risk Functions
                    </p>
                    <p className="text-3xl font-bold mt-2 text-red-500">
                      {totalHighRiskFunctions}
                    </p>
                  </div>

                  <div className="bg-slate-100 rounded-xl p-4">
                    <p className="text-sm text-slate-500">Average Complexity</p>
                    <p className="text-3xl font-bold mt-2 text-cyan-600">
                      {averageComplexity}
                    </p>
                  </div>
                </div>

                <h4 className="text-xl font-semibold text-slate-800 mb-4">
                  Files in this Report
                </h4>

                <div className="flex flex-wrap gap-3">
                  {folderResults.map((fileResult, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedResult(fileResult)}
                      className={`px-4 py-2 rounded-xl border transition ${
                        selectedResult?.file === fileResult.file
                          ? "bg-cyan-500 text-white border-cyan-500"
                          : "bg-white border-slate-300 text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      {getFileName(fileResult.file)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedResult && (
              <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-200">
                <h3 className="text-3xl font-bold text-slate-800 mb-6">
                  Opened Analysis Result
                </h3>

                <ResultSummary result={selectedResult} />
                <RiskSummary riskSummary={selectedResult.risk_summary} />
                <HighRiskFunctions
                  functions={selectedResult.high_risk_functions}
                />
                <Recommendations
                  recommendations={
                    selectedResult.intelligent_testing_context
                      .llm_test_recommendations
                  }
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AnalysisHistoryPage;