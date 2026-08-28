import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000";

export const uploadAndAnalyzeFile = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await axios.post(
    `${API_BASE_URL}/upload-and-analyze`,
    formData
  );

  return response.data;
};

export const analyzeFolder = async (folderPath) => {
  const response = await axios.post(
    `${API_BASE_URL}/analyze-folder`,
    {
      folder_path: folderPath,
    }
  );

  return response.data;
};

export const getAnalysisHistory = async () => {
  const response = await axios.get(
    `${API_BASE_URL}/analysis-results`
  );

  return response.data;
};

export const getDashboardStats = async () => {
  const response = await axios.get(
    `${API_BASE_URL}/dashboard-stats`
  );

  return response.data;
};

// --- New: requirement-aware analysis endpoints ---

// Analyze one file against a hand-authored requirement document (JSON/TXT)
export const analyzeWithRequirements = async (filePath, requirementPath) => {
  const response = await axios.post(
    `${API_BASE_URL}/analyze-with-requirements`,
    {
      file_path: filePath,
      requirement_path: requirementPath,
    }
  );

  return response.data;
};

// Analyze one file against requirements auto-extracted from its own
// docstrings/type hints -- no requirement file needed
export const analyzeWithAutoRequirements = async (filePath) => {
  const response = await axios.post(
    `${API_BASE_URL}/analyze-with-auto-requirements`,
    {
      file_path: filePath,
    }
  );

  return response.data;
};

// Clone a GitHub repo (or reuse an existing clone) and run
// requirement-aware analysis across every Python file in it
export const analyzeGithubRepo = async (repoUrl, forceReclone = false) => {
  const response = await axios.post(
    `${API_BASE_URL}/analyze-github-repo`,
    {
      repo_url: repoUrl,
      force_reclone: forceReclone,
    }
  );

  return response.data;
};


// Get the complete analysis report by its MongoDB ID
export const getAnalysisResult = async (reportId) => {
  const response = await axios.get(
    `${API_BASE_URL}/analysis-results/${reportId}`
  );

  return response.data;
};
