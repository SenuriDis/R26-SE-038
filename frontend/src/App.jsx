import { BrowserRouter, Routes, Route } from "react-router-dom";
import StaticAnalysisPage from "./pages/StaticAnalysisPage";
import Dashboard from "./pages/Dashboard";
import AnalysisHistoryPage from "./pages/AnalysisHistoryPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/analysis" element={<StaticAnalysisPage />} />
        <Route path="/history" element={<AnalysisHistoryPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;