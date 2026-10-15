import { useState } from "react";
import { analyzeGithubRepo } from "../services/api";

import {
  FileCode2,
  AlertTriangle,
  Activity,
  CheckCircle2,
  GitBranch,
} from "lucide-react";

import Navbar from "../components/Navbar";
import HeaderSection from "../components/HeaderSection";
import ScanConfigCard from "../components/ScanConfigCard";
import RequirementCoverageCard from "../components/RequirementCoverageCard";
import AnalysisResultView from "../components/AnalysisResultView";

function StaticAnalysisPage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [result, setResult] = useState(null);
  const [folderResults, setFolderResults] = useState([]);
  const [repoSummary, setRepoSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  // Success notification state
  const [successMessage, setSuccessMessage] = useState("");

  const showSuccessMessage = (message) => {
    setTimeout(() => {
      setSuccessMessage(message);

      setTimeout(() => {
        setSuccessMessage("");
      }, 3000);
    }, 200);
  };

  // Clone a GitHub repo and run requirement-aware analysis across
  // every Python file in it -- the only analysis entry point now
  const handleAnalyzeGithubRepo = async () => {
    if (!repoUrl) {
      alert("Please enter a GitHub repository URL");
      return;
    }

    try {
      setLoading(true);

      const data = await analyzeGithubRepo(repoUrl);

      if (data.error) {
        alert(data.error);
        setLoading(false);
        return;
      }

      if (Array.isArray(data.files) && data.files.length > 0) {
        setFolderResults(data.files);
        setResult(data.files[0]);
        setRepoSummary(data.repo_summary);

        showSuccessMessage(
          `Repository analyzed successfully! ${data.files.length} Python files, ${data.repo_summary.total_functions} functions.`
        );
      } else {
        setFolderResults([]);
        setResult(null);
        setRepoSummary(null);

        alert("No Python files found in this repository");
      }
    } catch (error) {
      console.error(error);
      alert("GitHub repository analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const getFileName = (filePath) => {
    return filePath.split("\\").pop().split("/").pop();
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
        <HeaderSection />

        {/* Success Notification */}
        {successMessage && (
          <div className="fixed top-6 right-6 z-50 bg-green-500 text-white px-6 py-4 rounded-2xl shadow-xl flex items-center gap-3 animate-bounce">
            <CheckCircle2 size={22} />

            <p className="font-medium">{successMessage}</p>
          </div>
        )}

        {/* Main Top Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* GitHub Repository Analysis */}
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
                  Analyze any public GitHub repository -- cloned
                  automatically, no manual setup required.
                </p>
              </div>
            </div>

            <div className="border-2 border-dashed border-slate-300 rounded-3xl p-10 bg-slate-50 text-center">
              <div className="bg-slate-800 w-20 h-20 rounded-3xl flex items-center justify-center mx-auto shadow-sm">
                <GitBranch size={34} className="text-white" />
              </div>

              <h3 className="text-2xl font-bold text-slate-800 mt-6">
                Analyze a GitHub Repository
              </h3>

              <p className="text-slate-500 mt-2">
                Paste a public repository URL -- it's cloned and analyzed
                automatically.
              </p>

              <div className="mt-8 max-w-xl mx-auto">
                <input
                  type="text"
                  placeholder="https://github.com/owner/repo.git"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full border border-slate-300 rounded-2xl px-5 py-4 outline-none focus:ring-2 focus:ring-cyan-400 bg-white"
                />
              </div>

              <button
                onClick={handleAnalyzeGithubRepo}
                className="mt-6 bg-slate-900 hover:bg-black text-white px-7 py-3 rounded-2xl font-medium transition"
              >
                {loading ? "Cloning & Analyzing..." : "Clone & Analyze"}
              </button>
            </div>
          </div>

          {/* Right Side */}
          <ScanConfigCard />
        </div>

        {/* Repo-level summary */}
        {repoSummary && (
          <RequirementCoverageCard projectSummary={repoSummary} />
        )}

        {/* Repository Overview */}
        {folderResults.length > 0 && (
          <div className="mt-8 bg-white rounded-3xl shadow-sm border border-slate-200 p-8">
            <h3 className="text-3xl font-bold text-slate-800 mb-8">
              Repository Analysis Overview
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-slate-100 rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Files Analyzed</p>

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
                    <p className="text-sm text-slate-500">High-Risk Functions</p>

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
                    <p className="text-sm text-slate-500">Average Complexity</p>

                    <h2 className="text-4xl font-bold mt-3 text-cyan-600">
                      {averageComplexity}
                    </h2>
                  </div>

                  <Activity className="text-cyan-600" size={26} />
                </div>
              </div>
            </div>

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

        {/* Analysis Result -- tabbed, see AnalysisResultView */}
        {result && (
          <div className="mt-8 bg-white rounded-3xl shadow-sm border border-slate-200 p-8">
            <h3 className="text-3xl font-bold text-slate-800 mb-8">
              Analysis Result
            </h3>

            <AnalysisResultView result={result} />
          </div>
        )}
      </div>
    </div>
  );
}

export default StaticAnalysisPage;
