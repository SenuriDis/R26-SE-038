import { useEffect, useState } from "react";
import {
  Clock3,
  RefreshCw,
  FolderOpen,
  FileCode2,
  Activity,
  AlertTriangle,
  Database,
  MousePointerClick,
} from "lucide-react";

import Navbar from "../components/Navbar";
import ResultSummary from "../components/ResultSummary";
import RiskSummary from "../components/RiskSummary";
import HighRiskFunctions from "../components/HighRiskFunctions";
import Recommendations from "../components/Recommendations";
import RequirementCoverageCard from "../components/RequirementCoverageCard";
import RequirementMappingTable from "../components/RequirementMappingTable";
import GapAnalysisPanel from "../components/GapAnalysisPanel";
import JsonViewer from "../components/JsonViewer";
import { getAnalysisHistory } from "../services/api";

function AnalysisHistoryPage() {
  const [history, setHistory] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [folderResults, setFolderResults] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

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

  const formatReportType = (type) => {
    return type.replaceAll("_", " ").toUpperCase();
  };

  const openReport = (item) => {
    setSelectedReport(item);

    if (item.results && item.results.length > 0) {
      // Folder analysis: per-file results at item.results
      setFolderResults(item.results);
      setSelectedResult(item.results[0]);
    } else if (item.result && Array.isArray(item.result.files)) {
      // GitHub repo analysis: per-file results nested at item.result.files,
      // not at item.result directly
      setFolderResults(item.result.files);
      setSelectedResult(item.result.files[0] || null);
    } else if (item.result) {
      // Single file analysis (upload, path, or requirement-aware)
      setFolderResults([]);
      setSelectedResult(item.result);
    } else {
      setFolderResults([]);
      setSelectedResult(null);
    }
  };

  const totalHighRiskFunctions = folderResults.reduce(
    (acc, item) => acc + (item.high_risk_functions?.length || 0),
    0
  );

  const averageComplexity =
    folderResults.length > 0
      ? (
          folderResults.reduce(
            (acc, item) => acc + (item.summary?.file_cyclomatic_complexity || 0),
            0
          ) / folderResults.length
        ).toFixed(1)
      : 0;

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />

      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <p className="text-cyan-600 font-semibold text-sm flex items-center gap-2">
            <Clock3 size={16} />
            RECENT RESULTS
          </p>

          <h1 className="text-4xl font-bold text-slate-800 mt-2">
            Recent Analysis Results
          </h1>

          <p className="text-slate-500 mt-2">
            View saved analysis reports stored in MongoDB Atlas and reopen
            previous file or folder analysis results.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Saved Reports */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-800">
                  Saved Reports
                </h2>

                <p className="text-sm text-slate-500 mt-1">
                  MongoDB stored analysis history
                </p>
              </div>

              <button
                onClick={loadHistory}
                className="bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-xl text-sm flex items-center gap-2"
              >
                <RefreshCw size={15} />
                Refresh
              </button>
            </div>

            {history.length > 0 ? (
              <div className="space-y-4 max-h-[680px] overflow-y-auto pr-2">
                {history.map((item) => {
                  const isFolder =
                    (item.results && item.results.length > 0) ||
                    (item.result && Array.isArray(item.result.files));

                  return (
                    <div
                      key={item._id}
                      onClick={() => openReport(item)}
                      className={`border rounded-2xl p-5 cursor-pointer transition hover:shadow-sm ${
                        selectedReport?._id === item._id
                          ? "bg-cyan-50 border-cyan-300"
                          : "bg-slate-50 border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`p-3 rounded-2xl ${
                            isFolder
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-cyan-100 text-cyan-700"
                          }`}
                        >
                          {isFolder ? (
                            <FolderOpen size={20} />
                          ) : (
                            <FileCode2 size={20} />
                          )}
                        </div>

                        <div className="flex-1">
                          <p className="font-bold text-slate-800">
                            {formatReportType(item.type)}
                          </p>

                          <p className="text-sm text-slate-500 mt-1">
                            {new Date(item.created_at).toLocaleString()}
                          </p>

                          {item.input_path && (
                            <p className="text-xs text-slate-500 mt-3 break-all">
                              Path: {item.input_path}
                            </p>
                          )}

                          {item.repo_url && (
                            <p className="text-xs text-slate-500 mt-3 break-all">
                              Repo: {item.repo_url}
                            </p>
                          )}

                          {item.file_name && (
                            <p className="text-xs text-slate-500 mt-3">
                              File: {item.file_name}
                            </p>
                          )}

                          <span className="inline-flex items-center gap-2 mt-4 bg-cyan-100 text-cyan-700 px-3 py-1 rounded-full text-xs">
                            <MousePointerClick size={13} />
                            Click to open
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center">
                <Database size={34} className="mx-auto text-slate-400" />

                <p className="text-slate-500 mt-3">
                  No saved reports found.
                </p>
              </div>
            )}
          </div>

          {/* Report Details */}
          <div className="lg:col-span-2">
            {!selectedResult && (
              <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-12 text-center">
                <div className="bg-cyan-100 text-cyan-700 w-16 h-16 rounded-3xl flex items-center justify-center mx-auto">
                  <MousePointerClick size={28} />
                </div>

                <h3 className="text-2xl font-bold text-slate-800 mt-5">
                  Select a Report
                </h3>

                <p className="text-slate-500 mt-2">
                  Choose a saved report from the left side to view analysis
                  details.
                </p>
              </div>
            )}

            {folderResults.length > 0 && (
              <div className="bg-white rounded-3xl shadow-sm p-6 border border-slate-200 mb-6">
                <h3 className="text-2xl font-bold text-slate-800 mb-6">
                  Folder Report Overview
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <div className="bg-slate-100 rounded-2xl p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-slate-500">
                          Files Analyzed
                        </p>

                        <p className="text-4xl font-bold mt-3">
                          {folderResults.length}
                        </p>
                      </div>

                      <FileCode2 className="text-cyan-600" size={25} />
                    </div>
                  </div>

                  <div className="bg-slate-100 rounded-2xl p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-slate-500">
                          High-Risk Functions
                        </p>

                        <p className="text-4xl font-bold mt-3 text-red-500">
                          {totalHighRiskFunctions}
                        </p>
                      </div>

                      <AlertTriangle className="text-red-500" size={25} />
                    </div>
                  </div>

                  <div className="bg-slate-100 rounded-2xl p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-slate-500">
                          Average Complexity
                        </p>

                        <p className="text-4xl font-bold mt-3 text-cyan-600">
                          {averageComplexity}
                        </p>
                      </div>

                      <Activity className="text-cyan-600" size={25} />
                    </div>
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
              <div className="bg-white rounded-3xl shadow-sm p-8 border border-slate-200">

    <h3 className="text-3xl font-bold text-slate-800 mb-6">
      Opened Analysis Result
    </h3>

    {/* Tabs */}
    <div className="flex gap-3 mb-8 border-b pb-4">
      <button
        onClick={() => setActiveTab("overview")}
        className={`px-5 py-2 rounded-xl ${
          activeTab === "overview"
            ? "bg-cyan-500 text-white"
            : "bg-slate-100"
        }`}
      >
        Overview
      </button>

      <button
        onClick={() => setActiveTab("requirements")}
        className={`px-5 py-2 rounded-xl ${
          activeTab === "requirements"
            ? "bg-cyan-500 text-white"
            : "bg-slate-100"
        }`}
      >
        Requirements
      </button>

      <button
        onClick={() => setActiveTab("json")}
        className={`px-5 py-2 rounded-xl ${
          activeTab === "json"
            ? "bg-cyan-500 text-white"
            : "bg-slate-100"
        }`}
      >
        Raw JSON
      </button>
    </div>

    {/* OVERVIEW TAB */}
    {activeTab === "overview" && (
      <>
        <ResultSummary result={selectedResult} />

        <RiskSummary
          riskSummary={selectedResult.risk_summary}
        />

        <HighRiskFunctions
          functions={selectedResult.high_risk_functions}
        />

        <Recommendations
          recommendations={
            selectedResult.intelligent_testing_context
              ?.llm_test_recommendations
          }
        />
      </>
    )}

    {/* REQUIREMENTS TAB */}
    {activeTab === "requirements" &&
      selectedResult.requirement_analysis && (
        <>
          <RequirementCoverageCard
            projectSummary={
              selectedResult.requirement_analysis.project_summary
            }
          />

          <RequirementMappingTable
            functions={
              selectedResult.requirement_analysis.functions
            }
          />

          <GapAnalysisPanel
            functions={
              selectedResult.requirement_analysis.functions
            }
          />
        </>
      )}

    {/* JSON TAB */}
    {activeTab === "json" && (
      <JsonViewer
        data={selectedResult}
        fileName="feature_matrix.json"
      />
    )}
  </div>
)}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AnalysisHistoryPage;
