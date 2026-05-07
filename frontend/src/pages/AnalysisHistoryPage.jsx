import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import { getAnalysisHistory } from "../services/api";

function AnalysisHistoryPage() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getAnalysisHistory();
      setHistory(data);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar />

      <div className="max-w-7xl mx-auto p-8">

        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800">
            Analysis History
          </h1>

          <p className="text-slate-500 mt-2">
            Previously analyzed files and project reports stored in MongoDB Atlas.
          </p>
        </div>

        <div className="space-y-5">

          {history.length > 0 ? (
            history.map((item) => (
              <div
                key={item._id}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6"
              >

                <div className="flex justify-between items-center">
                  <div>

                    <h3 className="text-xl font-semibold text-slate-800">
                      {item.type}
                    </h3>

                    <p className="text-sm text-slate-500 mt-1">
                      {new Date(item.created_at).toLocaleString()}
                    </p>

                    {item.input_path && (
                      <p className="text-sm text-slate-500 mt-2 break-all">
                        Path: {item.input_path}
                      </p>
                    )}

                    {item.file_name && (
                      <p className="text-sm text-slate-500 mt-2">
                        File: {item.file_name}
                      </p>
                    )}

                  </div>

                  <div className="bg-cyan-100 text-cyan-700 px-4 py-2 rounded-xl text-sm">
                    Saved
                  </div>

                </div>

              </div>
            ))
          ) : (
            <div className="bg-white rounded-2xl p-10 text-center border border-slate-200">
              <p className="text-slate-500">
                No analysis history found.
              </p>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}

export default AnalysisHistoryPage;