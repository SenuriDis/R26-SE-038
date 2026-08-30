import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export const checkHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const runPipeline = async (payload) => {
  const response = await api.post("/run", payload);
  return response.data;
};