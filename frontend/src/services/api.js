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
    `${API_BASE_URL}/analysis-results`
  );

  return response.data;
};