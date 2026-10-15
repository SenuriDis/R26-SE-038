import { useState } from "react";
import { Code2, Download, ChevronDown, ChevronUp } from "lucide-react";

// Shows the raw JSON behind whatever's currently displayed, with a
// download button. Collapsed by default -- click to expand.
function JsonViewer({ data, fileName = "feature_matrix.json" }) {
  const [expanded, setExpanded] = useState(false);

  if (!data) return null;

  const jsonText = JSON.stringify(data, null, 2);

  const handleDownload = () => {
    const blob = new Blob([jsonText], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();

    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-8 bg-white border border-slate-200 rounded-3xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-5 bg-slate-50">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-3 text-left"
        >
          <div className="bg-slate-800 text-white p-2 rounded-xl">
            <Code2 size={18} />
          </div>

          <div>
            <p className="font-bold text-slate-800">Raw JSON Output</p>
            <p className="text-xs text-slate-500">
              {expanded ? "Click to collapse" : "Click to view the full analysis output"}
            </p>
          </div>

          {expanded ? (
            <ChevronUp size={18} className="text-slate-400 ml-2" />
          ) : (
            <ChevronDown size={18} className="text-slate-400 ml-2" />
          )}
        </button>

        <button
          onClick={handleDownload}
          className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition"
        >
          <Download size={15} />
          Download JSON
        </button>
      </div>

      {expanded && (
        <pre className="max-h-[500px] overflow-auto text-xs bg-slate-900 text-slate-100 p-6 font-mono leading-relaxed">
          {jsonText}
        </pre>
      )}
    </div>
  );
}

export default JsonViewer;
