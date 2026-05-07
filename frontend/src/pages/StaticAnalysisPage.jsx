import { useState } from "react";
import {
  uploadAndAnalyzeFile,
  analyzeFolder,
  getAnalysisHistory,
} from "../services/api";

import Navbar from "../components/Navbar";
import HeaderSection from "../components/HeaderSection";
import SourceInputCard from "../components/SourceInputCard";
import ScanConfigCard from "../components/ScanConfigCard";
import ResultSummary from "../components/ResultSummary";
import RiskSummary from "../components/RiskSummary";
import HighRiskFunctions from "../components/HighRiskFunctions";
import Recommendations from "../components/Recommendations";
import HistoryPanel from "../components/HistoryPanel";

function StaticAnalysisPage() {
  const [file, setFile] = useState(null);
  const [folderPath, setFolderPath] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
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
        setResult(data[0]);
      } else {
        alert("No Python files found in this folder");
      }
    } catch (error) {
      console.error(error);
      alert("Folder analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await getAnalysisHistory();
      setHistory(data);
    } catch (error) {
      console.error(error);
      alert("Failed to load analysis history");
    }
  };

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

        <HistoryPanel history={history} onLoadHistory={loadHistory} />
      </div>
    </div>
  );
}

export default StaticAnalysisPage;