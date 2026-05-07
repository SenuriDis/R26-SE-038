function HistoryPanel({ history, onLoadHistory }) {
  return (
    <div className="mt-8 bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">
            Saved Analysis History
          </h3>
          <p className="text-sm text-slate-500">
            Results stored in MongoDB Atlas.
          </p>
        </div>

        <button
          onClick={onLoadHistory}
          className="bg-slate-800 hover:bg-slate-900 text-white px-5 py-2 rounded-lg"
        >
          Refresh History
        </button>
      </div>

      {history.length > 0 ? (
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item._id}
              className="bg-slate-50 border border-slate-200 rounded-xl p-4"
            >
              <p className="font-semibold text-slate-800">{item.type}</p>

              <p className="text-sm text-slate-500 mt-1">
                {new Date(item.created_at).toLocaleString()}
              </p>

              {item.input_path && (
                <p className="text-sm text-slate-500 mt-1 break-all">
                  Path: {item.input_path}
                </p>
              )}

              {item.file_name && (
                <p className="text-sm text-slate-500 mt-1">
                  File: {item.file_name}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-slate-500">
          No history loaded yet. Click Refresh History to view saved analysis
          results.
        </p>
      )}
    </div>
  );
}

export default HistoryPanel;