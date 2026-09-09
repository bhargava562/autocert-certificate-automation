import React, { useState } from 'react';
import { Download, ZoomIn, X, Mail, Send, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { getCertificateImageUrl } from '../services/certificateApi';

export default function CertificatePreview({ certificate, onResendEmail }) {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

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

  const handleEmailAction = async () => {
    if (!onResendEmail || isSending || !certificate.email) return;
    setIsSending(true);
    try {
      await onResendEmail(certificate);
    } catch {
      // Error handled in hook
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="preview-card">
      <div className="preview-toolbar">
        <div className="preview-participant-info">
          <h3>{certificate.participant_name}</h3>
          <p style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px', flexWrap: 'wrap' }}>
            {certificate.email && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Mail size={12} /> {certificate.email}
              </span>
            )}
            <span>•</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
              ID: {certificate.certificate_id}
            </span>
            {certificate.email_status && (
              <>
                <span>•</span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: certificate.email_status === 'Sent' ? '#10b981' : certificate.email_status.startsWith('Failed') ? '#f87171' : 'var(--text-secondary)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  {certificate.email_status === 'Sent' ? <Send size={11} /> : null}
                  {certificate.email_status}
                </span>
              </>
            )}
          </p>
        </div>

        <div className="preview-actions">
          {certificate.email && onResendEmail && (
            <button
              type="button"
              disabled={isSending}
              className="btn-secondary btn-sm"
              onClick={handleEmailAction}
              title={certificate.email_status === 'Sent' ? 'Resend certificate via Gmail SMTP' : 'Send certificate via Gmail SMTP'}
            >
              <RefreshCw size={14} className={isSending ? 'animate-spin' : ''} />
              <span>{isSending ? 'Sending...' : certificate.email_status === 'Sent' ? 'Resend Email' : 'Send Email'}</span>
            </button>
          )}

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
