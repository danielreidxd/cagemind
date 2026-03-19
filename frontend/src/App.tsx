import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { useAnalytics } from './hooks/useAnalytics';
import Navbar from './components/Navbar';
import LoadingScreen from './components/LoadingScreen';
import SandboxPage from './pages/SandboxPage';
import UpcomingPage from './pages/UpcomingPage';
import NextEventsPage from './pages/NextEventsPage';
import StatsPage from './pages/StatsPage';
import LoginPage from './pages/LoginPage';
import AdminPage from './pages/AdminPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppContent() {
  const [loading, setLoading] = useState(true);
  const handleFinish = useCallback(() => setLoading(false), []);
  useAnalytics(); // Auto-tracks page views on route change

  return (
    <>
      {loading && <LoadingScreen onFinish={handleFinish} duration={5200} />}
      <div className={`min-h-screen bg-ufc-dark ${loading ? 'overflow-hidden h-screen' : ''}`}>
        <Navbar />
        <main>
          <Routes>
            <Route path="/" element={<NextEventsPage />} />
            <Route path="/historico" element={<UpcomingPage />} />
            <Route path="/sandbox" element={<SandboxPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
          </Routes>
        </main>
        <footer className="text-center py-6 text-ufc-muted text-xs border-t border-ufc-border/30 mt-12">
          CageMind &middot; MMA Fight Intelligence &middot; Machine Learning Predictions
        </footer>
      </div>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}
