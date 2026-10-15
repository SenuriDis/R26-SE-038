function SourceInputCard({
  file,
  setFile,
  folderPath,
  setFolderPath,
  loading,
  onAnalyzeFile,
  onAnalyzeFolder,
}) {
  return (
    <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm p-6 border border-slate-200">
      <h3 className="text-2xl font-semibold text-slate-800 mb-6">
        Source Code Input
      </h3>

      <div className="border-2 border-dashed border-slate-300 rounded-2xl p-10 text-center bg-slate-50">
        <div className="text-5xl mb-4">📂</div>

        <p className="text-lg font-medium text-slate-700">
          Click to upload Python source file
        </p>

        <p className="text-sm text-slate-500 mt-1">
          Supports individual .py files
        </p>

        <input
          type="file"
          accept=".py"
          onChange={(e) => setFile(e.target.files[0])}
          className="mt-6 mx-auto block"
        />

        {file && (
          <div className="mt-5 bg-white border border-slate-200 rounded-xl p-3 text-left">
            <p className="font-medium text-slate-700">Selected File:</p>
            <p className="text-slate-500 text-sm mt-1">{file.name}</p>
          </div>
        )}
      </div>

      <button
        onClick={onAnalyzeFile}
        className="mt-6 bg-cyan-500 hover:bg-cyan-600 text-white px-6 py-3 rounded-xl font-medium transition"
      >
        {loading ? "Analyzing..." : "Analyze Uploaded File"}
      </button>

      <div className="mt-8 border-t border-slate-200 pt-6">
        <h4 className="text-lg font-semibold text-slate-700 mb-3">
          Analyze Local Project Folder
        </h4>

        <p className="text-sm text-slate-500 mb-3">
          Enter a local folder path to analyze all Python files inside a project
          directory.
        </p>

        <input
          type="text"
          placeholder="Example: C:/Users/micro/OneDrive/Desktop/recipe-app-python"
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          className="w-full border border-slate-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-cyan-400"
        />

        <button
          onClick={onAnalyzeFolder}
          className="mt-4 bg-slate-800 hover:bg-slate-900 text-white px-5 py-3 rounded-xl"
        >
          {loading ? "Analyzing..." : "Analyze Folder"}
        </button>
      </div>
    </div>
  );
}

export default SourceInputCard;