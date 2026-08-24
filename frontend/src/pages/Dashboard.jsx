import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileCode2,
  AlertTriangle,
  BrainCircuit,
  Activity,
  ArrowRight,
  Database,
  Sparkles,
} from "lucide-react";

import Navbar from "../components/Navbar";
import { getDashboardStats } from "../services/api";

function Dashboard() {
  const [stats, setStats] = useState({
    totalAnalyses: 0,
    totalHighRisk: 0,
    latestAnalysis: "N/A",
    avgComplexity: 0,
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const history = await getDashboardStats();

      let totalHighRisk = 0;
      let totalComplexity = 0;
      let complexityCount = 0;

      const tallyFileResult = (fileResult) => {
        totalHighRisk += fileResult.high_risk_functions?.length || 0;
        totalComplexity += fileResult.summary?.file_cyclomatic_complexity || 0;
        complexityCount++;
      };

      history.forEach((item) => {
        // Folder analysis result (array of per-file results)
        if (item.results) {
          item.results.forEach(tallyFileResult);
        }
        // GitHub repo analysis result -- per-file results are nested
        // inside item.result.files, not at item.result directly
        else if (item.result && Array.isArray(item.result.files)) {
          item.result.files.forEach(tallyFileResult);
        }
        // Single file analysis result (upload, path, or requirement-aware)
        else if (item.result) {
          tallyFileResult(item.result);
        }
      });

      const avgComplexity =
        complexityCount > 0
          ? (totalComplexity / complexityCount).toFixed(1)
          : 0;

      const latest =
        history.length > 0
          ? new Date(history[0].created_at).toLocaleString()
          : "N/A";

      setStats({
        totalAnalyses: history.length,
        totalHighRisk,
        latestAnalysis: latest,
        avgComplexity,
      });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />

      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-5 mb-8">
          <div>
            <p className="text-cyan-600 font-semibold text-sm flex items-center gap-2">
              <Sparkles size={16} />
              INTELLIGENT TESTING DASHBOARD
            </p>

            <h1 className="text-4xl font-bold text-slate-800 mt-2">
              Project Dashboard
            </h1>

            <p className="text-slate-500 mt-2">
              Intelligent static code analysis and testing recommendation
              platform.
            </p>
          </div>

          <Link
            to="/analysis"
            className="bg-cyan-500 hover:bg-cyan-600 text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2 shadow-sm transition"
          >
            + New Code Analysis
            <ArrowRight size={18} />
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-500 text-sm">Total Analyses</p>

                <h2 className="text-4xl font-bold mt-3 text-slate-800">
                  {stats.totalAnalyses}
                </h2>

                <p className="text-green-600 text-sm mt-2">
                  MongoDB connected
                </p>
              </div>

              <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
                <FileCode2 size={22} />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-500 text-sm">High-Risk Functions</p>

                <h2 className="text-4xl font-bold mt-3 text-red-500">
                  {stats.totalHighRisk}
                </h2>

                <p className="text-slate-500 text-sm mt-2">
                  Intelligent detection
                </p>
              </div>

              <div className="bg-red-100 text-red-600 p-3 rounded-xl">
                <AlertTriangle size={22} />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-500 text-sm">Avg Complexity</p>

                <h2 className="text-4xl font-bold mt-3 text-cyan-600">
                  {stats.avgComplexity}
                </h2>

                <p className="text-slate-500 text-sm mt-2">
                  Real-time calculation
                </p>
              </div>

              <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
                <Activity size={22} />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="flex justify-between items-start gap-3">
              <div>
                <p className="text-slate-500 text-sm">Latest Analysis</p>

                <h2 className="text-base font-bold mt-3 text-slate-800 break-words">
                  {stats.latestAnalysis}
                </h2>

                <p className="text-slate-500 text-sm mt-2">
                  Last stored report
                </p>
              </div>

              <div className="bg-purple-100 text-purple-700 p-3 rounded-xl shrink-0">
                <BrainCircuit size={22} />
              </div>
            </div>
          </div>
        </div>

        {/* Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-slate-100 text-slate-700 p-3 rounded-xl">
                <Database size={22} />
              </div>

              <h3 className="text-2xl font-bold text-slate-800">
                Platform Overview
              </h3>
            </div>

            <p className="text-slate-600 leading-8">
              This intelligent software testing platform performs AST-based
              static code analysis to identify structural risks, cyclomatic
              complexity patterns, dependency hotspots, and intelligent testing
              opportunities.
            </p>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-100 rounded-xl p-5">
                <h4 className="font-semibold text-slate-700">
                  Structural Analysis
                </h4>

                <p className="text-sm text-slate-500 mt-2 leading-6">
                  Extracts function details, control flow counts, nesting depth,
                  cyclomatic complexity, and dependencies.
                </p>
              </div>

              <div className="bg-slate-100 rounded-xl p-5">
                <h4 className="font-semibold text-slate-700">
                  AI-Ready Output
                </h4>

                <p className="text-sm text-slate-500 mt-2 leading-6">
                  Produces ML-ready features and LLM-ready testing
                  recommendations for intelligent test generation.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-cyan-50 rounded-2xl border border-cyan-100 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="bg-cyan-100 text-cyan-700 p-3 rounded-xl">
                <BrainCircuit size={22} />
              </div>

              <h3 className="text-xl font-semibold text-cyan-700">
                AI Suggestion
              </h3>
            </div>

            <p className="text-slate-600 text-sm leading-7">
              Analyze multiple repositories and compare complexity trends to
              improve testing prioritization and defect prediction.
            </p>

            <Link
              to="/history"
              className="inline-flex items-center gap-2 mt-6 text-cyan-700 font-medium hover:underline"
            >
              View recent results
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
