import { useState } from "react";
import {
  uploadAndAnalyzeFile,
  analyzeFolder,
} from "../services/api";

import Navbar from "../components/Navbar";
import HeaderSection from "../components/HeaderSection";
import SourceInputCard from "../components/SourceInputCard";
import ScanConfigCard from "../components/ScanConfigCard";
import ResultSummary from "../components/ResultSummary";
import RiskSummary from "../components/RiskSummary";
import HighRiskFunctions from "../components/HighRiskFunctions";
import Recommendations from "../components/Recommendations";

function StaticAnalysisPage() {
  const [file, setFile] = useState(null);
  const [folderPath, setFolderPath] = useState("");
  const [result, setResult] = useState(null);
  const [folderResults, setFolderResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAnalyzeFile = async () => {
    if (!file) {
      alert("Please upload a Python file");
      return;
    }

    try {
      setLoading(true);
      const data = await uploadAndAnalyzeFile(file);
      setResult(data);
      setFolderResults([]);
    } catch (error) {
      console.error(error);
      alert("File analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeFolder = async () => {
    if (!folderPath) {
      alert("Please enter folder path");
      return;
    }

    try {
      setLoading(true);
      const data = await analyzeFolder(folderPath);

      if (Array.isArray(data) && data.length > 0) {
        setFolderResults(data);
        setResult(data[0]);
      } else {
        setFolderResults([]);
        setResult(null);
        alert("No Python files found in this folder");
      }
    } catch (error) {
      console.error(error);
      alert("Folder analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const getFileName = (filePath) => {
    return filePath.split("\\").pop().split("/").pop();
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
        <HeaderSection />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SourceInputCard
            file={file}
            setFile={setFile}
            folderPath={folderPath}
            setFolderPath={setFolderPath}
            loading={loading}
            onAnalyzeFile={handleAnalyzeFile}
            onAnalyzeFolder={handleAnalyzeFolder}
          />

          <ScanConfigCard />
        </div>

        {folderResults.length > 0 && (
          <div className="mt-8 bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
            <h3 className="text-2xl font-bold text-slate-800 mb-6">
              Folder Analysis Overview
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
              Analyzed Files
            </h4>

            <div className="flex flex-wrap gap-3">
              {folderResults.map((fileResult, index) => (
                <button
                  key={index}
                  onClick={() => setResult(fileResult)}
                  className={`px-4 py-2 rounded-xl border transition ${
                    result?.file === fileResult.file
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

        {result && (
          <div className="mt-8 bg-white rounded-2xl shadow-sm p-8 border border-slate-200">
            <h3 className="text-3xl font-bold text-slate-800 mb-6">
              Analysis Result
            </h3>

            <ResultSummary result={result} />
            <RiskSummary riskSummary={result.risk_summary} />
            <HighRiskFunctions functions={result.high_risk_functions} />
            <Recommendations
              recommendations={
                result.intelligent_testing_context.llm_test_recommendations
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default StaticAnalysisPage;