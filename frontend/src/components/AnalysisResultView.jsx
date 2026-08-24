import { useState } from "react";
import {
  LayoutDashboard,
  Sparkles,
  ClipboardList,
  ShieldAlert,
} from "lucide-react";

import ResultSummary from "./ResultSummary";
import RiskSummary from "./RiskSummary";
import HighRiskFunctions from "./HighRiskFunctions";
import Recommendations from "./Recommendations";
import RequirementCoverageCard from "./RequirementCoverageCard";
import RequirementMappingTable from "./RequirementMappingTable";
import GapAnalysisPanel from "./GapAnalysisPanel";
import JsonViewer from "./JsonViewer";

// Renders one analysis result as a tabbed view instead of one long
// scrolling stack. Used by BOTH StaticAnalysisPage (live results) and
// AnalysisHistoryPage (saved reports) -- keeping this logic in one
// shared place means the two pages can't drift out of sync again.
function AnalysisResultView({ result }) {
  const hasRequirementAnalysis = Boolean(result?.requirement_analysis);

  const tabs = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "recommendations", label: "Recommendations", icon: Sparkles },
    ...(hasRequirementAnalysis
      ? [
          { id: "requirements", label: "Requirement Analysis", icon: ClipboardList },
          { id: "gaps", label: "Gap Analysis", icon: ShieldAlert },
        ]
      : []),
  ];

  const [activeTab, setActiveTab] = useState("overview");

  if (!result) return null;

  return (
    <div>
      {/* Tab bar */}
      <div className="flex flex-wrap gap-3 mb-8 border-b border-slate-200 pb-6">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 rounded-2xl font-medium transition ${
                isActive
                  ? "bg-cyan-500 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <Icon size={17} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <>
          <ResultSummary result={result} />
          <RiskSummary riskSummary={result.risk_summary} />
          <HighRiskFunctions functions={result.high_risk_functions} />
        </>
      )}

      {activeTab === "recommendations" && (
        <Recommendations
          recommendations={
            result.intelligent_testing_context?.llm_test_recommendations
          }
        />
      )}

      {activeTab === "requirements" && hasRequirementAnalysis && (
        <>
          <RequirementCoverageCard
            projectSummary={result.requirement_analysis.project_summary}
          />
          <RequirementMappingTable
            functions={result.requirement_analysis.functions}
          />
        </>
      )}

      {activeTab === "gaps" && hasRequirementAnalysis && (
        <GapAnalysisPanel functions={result.requirement_analysis.functions} />
      )}

      {/* Raw JSON stays pinned below the tabs regardless of which tab is
          active -- always findable, never the main event. Collapsed by
          default (see JsonViewer), so it doesn't add to page length
          unless someone actually opens it. */}
      <JsonViewer data={result} fileName="feature_matrix.json" />
    </div>
  );
}

export default AnalysisResultView;
