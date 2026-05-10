import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import NewPrediction from './pages/NewPrediction';
import RecentResults from './pages/RecentResults';
import ModelManagement from './pages/ModelManagement';
import { ToastProvider } from './context/ToastContext';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Navbar />
        <Routes>
          <Route path="/"        element={<Dashboard />} />
          <Route path="/predict" element={<NewPrediction />} />
          <Route path="/results" element={<RecentResults />} />
          <Route path="/model"   element={<ModelManagement />} />
        </Routes>
      </ToastProvider>
    </BrowserRouter>
  );
}
