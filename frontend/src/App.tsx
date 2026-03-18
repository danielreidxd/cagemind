import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LoadingScreen from './components/LoadingScreen';
import SandboxPage from './pages/SandboxPage';
import UpcomingPage from './pages/UpcomingPage';
import NextEventsPage from './pages/NextEventsPage';
import StatsPage from './pages/StatsPage';

export default function App() {
  const [loading, setLoading] = useState(true);
  const handleFinish = useCallback(() => setLoading(false), []);

  return (
    <>
      {loading && <LoadingScreen onFinish={handleFinish} duration={5200} />}
      <BrowserRouter>
        <div className={`min-h-screen bg-ufc-dark ${loading ? 'overflow-hidden h-screen' : ''}`}>
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<NextEventsPage />} />
              <Route path="/historico" element={<UpcomingPage />} />
              <Route path="/sandbox" element={<SandboxPage />} />
              <Route path="/stats" element={<StatsPage />} />
            </Routes>
          </main>
          <footer className="text-center py-6 text-ufc-muted text-xs border-t border-ufc-border/30 mt-12">
            CageMind &middot; MMA Fight Intelligence &middot; Machine Learning Predictions
          </footer>
        </div>
      </BrowserRouter>
    </>
  );
}
