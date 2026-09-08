import React, { useState } from 'react';
import { Download, ZoomIn, X, Mail, ShieldCheck, Loader2 } from 'lucide-react';
import { getCertificateImageUrl } from '../services/certificateApi';

export default function CertificatePreview({ certificate }) {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);

  if (!certificate) {
    return (
      <div className="preview-card" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
        Select a participant from the list to view their generated certificate PNG.
      </div>
    );
  }

  const imageUrl = getCertificateImageUrl(certificate.filename);

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = certificate.filename || `${certificate.certificate_id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="preview-card">
      <div className="preview-toolbar">
        <div className="preview-participant-info">
          <h3>{certificate.participant_name}</h3>
          <p style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
            {certificate.email && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Mail size={12} /> {certificate.email}
              </span>
            )}
            <span>•</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
              ID: {certificate.certificate_id}
            </span>
          </p>
        </div>

        <div className="preview-actions">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => setIsZoomed(true)}
            title="Zoom into certificate"
          >
            <ZoomIn size={14} />
            <span>Zoom</span>
          </button>

          <button
            type="button"
            className="btn-primary btn-sm"
            onClick={handleDownload}
            title="Download high-resolution PNG"
          >
            <Download size={14} />
            <span>Download PNG</span>
          </button>
        </div>
      </div>

      <div className="image-canvas-wrapper">
        {isImageLoading && (
          <div style={{ position: 'absolute', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
            <Loader2 size={24} className="animate-spin" color="#10b981" />
            <span>Loading certificate...</span>
          </div>
        )}

        <img
          key={imageUrl}
          src={imageUrl}
          alt={`Certificate for ${certificate.participant_name}`}
          className="cert-image-display"
          onLoad={() => setIsImageLoading(false)}
          onError={() => setIsImageLoading(false)}
          onClick={() => setIsZoomed(true)}
          title="Click to zoom"
        />
      </div>

      {/* Fullscreen Zoom Modal */}
      {isZoomed && (
        <div className="modal-overlay" onClick={() => setIsZoomed(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="modal-close-btn"
              onClick={() => setIsZoomed(false)}
              aria-label="Close Zoom"
            >
              <X size={28} />
            </button>
            <img
              src={imageUrl}
              alt={`Fullscreen certificate for ${certificate.participant_name}`}
              className="modal-image"
            />
            <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
              <button type="button" className="btn-primary" onClick={handleDownload}>
                <Download size={16} />
                <span>Download PNG</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
