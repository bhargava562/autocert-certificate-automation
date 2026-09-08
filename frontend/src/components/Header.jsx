import React from 'react';
import { Award, Server, AlertCircle } from 'lucide-react';

export default function Header({ backendConnected }) {
  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <div className="brand-logo">
          <Award size={28} />
        </div>
        <div>
          <h1 className="brand-title">Certificate Automation</h1>
          <p className="brand-subtitle">
            Generate personalized certificates from your template and participant data.
          </p>
        </div>
      </div>

      <div className="header-status">
        <span className={`status-dot ${backendConnected ? '' : 'offline'}`} />
        <span>{backendConnected ? 'Backend Connected' : 'Backend Offline'}</span>
      </div>
    </header>
  );
}
