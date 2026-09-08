import React from 'react';
import { Loader2, AlertCircle } from 'lucide-react';

export default function GenerationProgress({ isGenerating, totalCount, progressText, error }) {
  if (!isGenerating && !error) return null;

  return (
    <div className="progress-box">
      {isGenerating ? (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <Loader2 size={20} className="animate-spin" color="#10b981" />
            <h4 style={{ fontSize: '15px', fontWeight: 600 }}>
              Generating Certificates...
            </h4>
          </div>

          <div className="progress-bar-bg">
            <div className="progress-bar-fill" style={{ width: '100%' }} />
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {progressText || `Processing ${totalCount} certificates via backend engine...`}
          </p>
        </div>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: '#f87171' }}>
          <AlertCircle size={18} />
          <span style={{ fontSize: '13px', fontWeight: 500 }}>{error}</span>
        </div>
      ) : null}
    </div>
  );
}
