import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

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

      history.forEach((item) => {

        // folder analysis
        if (item.results) {
          item.results.forEach((result) => {
            totalHighRisk += result.high_risk_functions.length;

            totalComplexity +=
              result.summary.file_cyclomatic_complexity;

            complexityCount++;
          });
        }

        // single file analysis
        if (item.result) {
          totalHighRisk += item.result.high_risk_functions.length;

          totalComplexity +=
            item.result.summary.file_cyclomatic_complexity;

          complexityCount++;
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
        <div className="flex justify-between items-center mb-8">

          <div>
            <h1 className="text-4xl font-bold text-slate-800">
              Project Dashboard
            </h1>

            <p className="text-slate-500 mt-2">
              Intelligent static code analysis and testing recommendation platform.
            </p>
          </div>

          <Link
            to="/analysis"
            className="bg-cyan-500 hover:bg-cyan-600 text-white px-6 py-3 rounded-xl font-medium"
          >
            + New Code Analysis
          </Link>

        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">

            <p className="text-slate-500 text-sm">
              Total Analyses
            </p>

            <h2 className="text-4xl font-bold mt-3 text-slate-800">
              {stats.totalAnalyses}
            </h2>

            <p className="text-green-600 text-sm mt-2">
              MongoDB connected
            </p>

          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">

            <p className="text-slate-500 text-sm">
              High-Risk Functions
            </p>

            <h2 className="text-4xl font-bold mt-3 text-red-500">
              {stats.totalHighRisk}
            </h2>

            <p className="text-slate-500 text-sm mt-2">
              Intelligent detection
            </p>

          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">

            <p className="text-slate-500 text-sm">
              Avg Complexity
            </p>

            <h2 className="text-4xl font-bold mt-3 text-cyan-600">
              {stats.avgComplexity}
            </h2>

            <p className="text-slate-500 text-sm mt-2">
              Real-time calculation
            </p>

          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">

            <p className="text-slate-500 text-sm">
              Latest Analysis
            </p>

            <h2 className="text-lg font-bold mt-3 text-slate-800">
              {stats.latestAnalysis}
            </h2>

            <p className="text-slate-500 text-sm mt-2">
              Last stored report
            </p>

          </div>

        </div>

        {/* Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">

          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-8">

            <h3 className="text-2xl font-bold text-slate-800 mb-4">
              Platform Overview
            </h3>

            <p className="text-slate-600 leading-8">
              This intelligent software testing platform performs AST-based
              static code analysis to identify structural risks,
              cyclomatic complexity patterns, dependency hotspots,
              and intelligent testing opportunities.
            </p>

          </div>

          <div className="bg-cyan-50 rounded-2xl border border-cyan-100 p-6">

            <h3 className="text-xl font-semibold text-cyan-700 mb-3">
              AI Suggestion
            </h3>

            <p className="text-slate-600 text-sm leading-7">
              Analyze multiple repositories and compare complexity trends
              to improve testing prioritization and defect prediction.
            </p>

          </div>

        </div>

      </div>
    </div>
  );
}

export default Dashboard;