import Logo from './Logo';
import StatusIndicator from './StatusIndicator';

export default function Navbar({ isBackendOnline = true }) {
  return (
    <header className="navbar">
      <div className="navbar-container">
        {/* LEFT: AuraRAG logo + AuraRAG */}
        <div className="navbar-left">
          <div className="brand-badge">
            <Logo size={26} className="navbar-logo" />
            <span className="brand-name">AuraRAG</span>
          </div>
        </div>

        {/* CENTER: Voice RAG Agent */}
        <div className="navbar-center">
          <span className="nav-agent-label">Voice RAG Agent</span>
        </div>

        {/* RIGHT: AI Voice RAG + status indicator */}
        <div className="navbar-right">
          <span className="nav-tagline">AI Voice RAG</span>
          <StatusIndicator
            isOnline={isBackendOnline}
            label={isBackendOnline ? 'Online' : 'Offline'}
          />
        </div>
      </div>
    </header>
  );
}
