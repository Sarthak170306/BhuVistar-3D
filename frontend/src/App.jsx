import { useState, useEffect } from 'react';
import './App.css';
import Cadastral3DViewer from './components/Cadastral3DViewer';
import UlpinGenerator from './components/UlpinGenerator';
import { checkBackendHealth } from './services/cadastralApi';
import AuthProvider from './context/AuthContext';
import { useAuth } from './context/useAuth';
import Login from './pages/Login';
import OfficialPortal from './pages/OfficialPortal';
import AdminPortal from './pages/AdminPortal';

function CadastralWorkspace() {
  const { user, logout } = useAuth();
  const [activeUlpin, setActiveUlpin] = useState('BV3D-UP-NOI-55443322-B001-B02-UP32-PRK');
  const [activeUnitId, setActiveUnitId] = useState('c1f7b4e2-8924-4d89-9a28-98e3b1c1e555');
  const [generationKey, setGenerationKey] = useState(0);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'

  const handleUlpinGenerated = (ulpin, unitId) => {
    setActiveUlpin(ulpin);
    if (unitId) {
      setActiveUnitId(unitId);
    }
    setGenerationKey((k) => k + 1);
  };

  useEffect(() => {
    let isMounted = true;

    const runHealthCheck = async () => {
      try {
        const result = await checkBackendHealth(5000);
        if (!isMounted) return;
        setBackendStatus(result.connected ? 'connected' : 'disconnected');
      } catch {
        if (!isMounted) return;
        setBackendStatus('disconnected');
      }
    };

    // Immediate initial check on startup
    runHealthCheck();

    // Lightweight 12-second polling interval
    const intervalId = setInterval(runHealthCheck, 12000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="cadastral-app">
      {/* HEADER */}
      <header className="cadastral-header">
        <div className="cadastral-header__brand">
          <span className="cadastral-header__icon" aria-hidden="true">📐</span>
          <div className="cadastral-header__titles">
            <h1 className="cadastral-header__title">BhuVistaar 3D</h1>
            <span className="cadastral-header__subtitle">3D Cadastral Spatial Viewer</span>
          </div>
        </div>

        <div className="cadastral-header__right">
          {/* Authenticated User Metadata Chip */}
          <div className="cadastral-header__user" title={`Logged in as ${user?.name} (${user?.email})`}>
            <span className="user-role-badge">CITIZEN</span>
            <span className="user-name-label">{user?.name || 'Citizen'}</span>
          </div>

          <button
            type="button"
            className="cadastral-header__logout"
            onClick={logout}
            title="Sign out of current citizen session"
          >
            Sign Out
          </button>

          {/* Backend Status Indicator */}
          <div className={`cadastral-header__status cadastral-header__status--${backendStatus}`}>
            <span className={`status-dot status-dot--${backendStatus}`} aria-hidden="true" />
            <span className="status-label">
              {backendStatus === 'connected' && 'Backend Connected'}
              {backendStatus === 'checking' && 'Connecting...'}
              {backendStatus === 'disconnected' && 'Backend Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* MAIN THREE-REGION WORKSPACE */}
      <main className="cadastral-workspace">
        {/* LEFT PANEL: Compact ULPIN Generator */}
        <aside className="cadastral-panel-left" aria-label="ULPIN Specification and Generator">
          <UlpinGenerator onUlpinGenerated={handleUlpinGenerated} />
        </aside>

        {/* CENTER (3D Viewport) & RIGHT (Property Details) via Cadastral3DViewer */}
        <Cadastral3DViewer activeUlpin={activeUlpin} activeUnitId={activeUnitId} generationKey={generationKey} />
      </main>

      {/* BOTTOM / STATUS */}
      <footer className="cadastral-statusbar">
        <div className="statusbar-left">
          <span className="statusbar-indicator" aria-hidden="true" />
          <span className="statusbar-text">System ready</span>
        </div>
        <div className="statusbar-right">
          <span>EPSG:4326 PostGIS 3D Cadastre</span>
          <span className="statusbar-sep" aria-hidden="true">•</span>
          <span>Level 04 Volumetric Spatial Units</span>
        </div>
      </footer>
    </div>
  );
}

function AppContent() {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="cadastral-auth-loading">
        <span className="spinner" aria-hidden="true" style={{ width: 28, height: 28 }} />
        <span>Verifying Cadastral Authentication Credentials...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  // Role-Based Routing
  if (user?.role === 'OFFICIAL') {
    return <OfficialPortal />;
  }

  if (user?.role === 'ADMIN') {
    return <AdminPortal />;
  }

  // CITIZEN: Render Existing BhuVistaar 3D interface
  return <CadastralWorkspace />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
