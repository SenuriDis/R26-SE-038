import { useState } from "react";
import {
  uploadAndAnalyzeFile,
  analyzeFolder,
} from "../services/api";

import {
  FolderSearch,
  FileCode2,
  AlertTriangle,
  Activity,
  CheckCircle2,
} from "lucide-react";

import Navbar from "../components/Navbar";
import HeaderSection from "../components/HeaderSection";
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

  // Success notification state
  const [successMessage, setSuccessMessage] = useState("");

  // Show success message for 3 seconds
  const showSuccessMessage = (message) => {
  setTimeout(() => {
    setSuccessMessage(message);

    setTimeout(() => {
      setSuccessMessage("");
    }, 3000);

  }, 200);
};

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

      // Success message
      showSuccessMessage("Python file analyzed successfully!");
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

        // Success message
        showSuccessMessage(
          `Folder analysis completed successfully! ${data.length} Python files analyzed.`
        );
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

        {/* Success Notification */}
        {successMessage && (
          <div className="fixed top-6 right-6 z-50 bg-green-500 text-white px-6 py-4 rounded-2xl shadow-xl flex items-center gap-3 animate-bounce">
            
            <CheckCircle2 size={22} />
            
            <p className="font-medium">
              
              {successMessage}
              </p>
              
              </div>
            )}

        {/* Main Top Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Upload Section */}
          <div className="lg:col-span-2 bg-white rounded-3xl shadow-sm border border-slate-200 p-8">

            <div className="flex items-center gap-3 mb-6">

              <div className="bg-cyan-100 text-cyan-700 p-3 rounded-2xl">
                <FileCode2 size={24} />
              </div>

              <div>
                <h2 className="text-2xl font-bold text-slate-800">
                  Source Code Analysis
                </h2>

                <p className="text-slate-500 text-sm mt-1">
                  Upload Python files or analyze project repositories.
                </p>
              </div>

            </div>

            {/* Upload Box */}
            <div className="border-2 border-dashed border-slate-300 rounded-3xl p-10 bg-slate-50 text-center">

              <div className="bg-yellow-100 w-20 h-20 rounded-3xl flex items-center justify-center mx-auto shadow-sm border border-yellow-200">
                <FolderSearch size={34} className="text-yellow-600" />
              </div>

              <h3 className="text-2xl font-bold text-slate-800 mt-6">
                Upload Python Source File
              </h3>

              <p className="text-slate-500 mt-2">
                Supports individual <span className="font-semibold">.py</span> files
              </p>

              {/* Better File Input */}
              <div className="mt-8">

                <label className="cursor-pointer inline-flex items-center gap-3 bg-cyan-500 hover:bg-cyan-600 text-white px-6 py-3 rounded-2xl transition shadow-sm">

                  <FileCode2 size={18} />

                  <span>
                    Choose Python File
                  </span>

                  <input
                    type="file"
                    accept=".py"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="hidden"
                  />
                </label>

              </div>

              {/* Selected File */}
              {file && (
                <div className="mt-6 bg-white border border-slate-200 rounded-2xl p-4 max-w-md mx-auto">

                  <p className="text-sm text-slate-500">
                    Selected File
                  </p>

                  <p className="font-semibold text-slate-800 mt-1">
                    {file.name}
                  </p>

                </div>
              )}

              <button
                onClick={handleAnalyzeFile}
                className="mt-8 bg-slate-900 hover:bg-black text-white px-7 py-3 rounded-2xl font-medium transition"
              >
                {loading ? "Analyzing..." : "Start File Analysis"}
              </button>

            </div>

            {/* Folder Analysis */}
            <div className="mt-8 bg-slate-50 border border-slate-200 rounded-3xl p-6">

              <div className="flex items-center gap-3 mb-4">

                <div className="bg-purple-100 text-purple-700 p-3 rounded-2xl">
                  <FolderSearch size={22} />
                </div>

                <div>
                  <h3 className="text-xl font-bold text-slate-800">
                    Repository / Folder Analysis
                  </h3>

                  <p className="text-sm text-slate-500 mt-1">
                    Analyze all Python files inside a project folder.
                  </p>
                </div>

              </div>

              <input
                type="text"
                placeholder="C:/Users/micro/Desktop/project-folder"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                className="w-full border border-slate-300 rounded-2xl px-5 py-4 outline-none focus:ring-2 focus:ring-cyan-400 bg-white"
              />

              <button
                onClick={handleAnalyzeFolder}
                className="mt-5 bg-cyan-500 hover:bg-cyan-600 text-white px-6 py-3 rounded-2xl transition"
              >
                {loading ? "Analyzing..." : "Analyze Folder"}
              </button>

            </div>

          </div>

          {/* Right Side */}
          <ScanConfigCard />
        </div>

        {/* Folder Overview */}
        {folderResults.length > 0 && (
          <div className="mt-8 bg-white rounded-3xl shadow-sm border border-slate-200 p-8">

            <h3 className="text-3xl font-bold text-slate-800 mb-8">
              Folder Analysis Overview
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

              <div className="bg-slate-100 rounded-2xl p-5">
                <div className="flex items-center justify-between">

                  <div>
                    <p className="text-sm text-slate-500">
                      Files Analyzed
                    </p>

                    <h2 className="text-4xl font-bold mt-3">
                      {folderResults.length}
                    </h2>
                  </div>

                  <FileCode2 className="text-cyan-600" size={26} />

                </div>
              </div>

              <div className="bg-slate-100 rounded-2xl p-5">
                <div className="flex items-center justify-between">

                  <div>
                    <p className="text-sm text-slate-500">
                      High-Risk Functions
                    </p>

                    <h2 className="text-4xl font-bold mt-3 text-red-500">
                      {totalHighRiskFunctions}
                    </h2>
                  </div>

                  <AlertTriangle className="text-red-500" size={26} />

                </div>
              </div>

              <div className="bg-slate-100 rounded-2xl p-5">
                <div className="flex items-center justify-between">

                  <div>
                    <p className="text-sm text-slate-500">
                      Average Complexity
                    </p>

                    <h2 className="text-4xl font-bold mt-3 text-cyan-600">
                      {averageComplexity}
                    </h2>
                  </div>

                  <Activity className="text-cyan-600" size={26} />

                </div>
              </div>

            </div>

            {/* File Buttons */}
            <div className="mt-10">

              <h4 className="text-xl font-semibold text-slate-800 mb-5">
                Analyzed Files
              </h4>

              <div className="flex flex-wrap gap-3">

                {folderResults.map((fileResult, index) => (
                  <button
                    key={index}
                    onClick={() => setResult(fileResult)}
                    className={`px-5 py-3 rounded-2xl border transition ${
                      result?.file === fileResult.file
                        ? "bg-cyan-500 text-white border-cyan-500 shadow-sm"
                        : "bg-white border-slate-300 text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {getFileName(fileResult.file)}
                  </button>
                ))}

              </div>

            </div>

          </div>
        )}

        {/* Analysis Result */}
        {result && (
          <div className="mt-8 bg-white rounded-3xl shadow-sm border border-slate-200 p-8">

            <h3 className="text-3xl font-bold text-slate-800 mb-8">
              Analysis Result
            </h3>

            <ResultSummary result={result} />

            <RiskSummary riskSummary={result.risk_summary} />

            <HighRiskFunctions
              functions={result.high_risk_functions}
            />

            <Recommendations
              recommendations={
                result.intelligent_testing_context
                  .llm_test_recommendations
              }
            />

          </div>
        )}

      </div>
    </div>
  );
}

export default StaticAnalysisPage;