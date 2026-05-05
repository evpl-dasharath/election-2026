import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ConstituencyPage from './pages/ConstituencyPage';
import AdminPanel from './pages/AdminPanel';
import HistoryPage from './pages/HistoryPage';
import AlliancePage from './pages/AlliancePage';
import PartyPage from './pages/PartyPage';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/constituency/:id" element={<ConstituencyPage />} />
        <Route path="/alliance/:code" element={<AlliancePage />} />
        <Route path="/party" element={<PartyPage />} />
        <Route path="/party/:code" element={<PartyPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
