import React, { useState, useMemo } from 'react';
import { Search, Mail, Send, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

export default function CertificateList({
  certificates = [],
  selectedId,
  onSelectCertificate,
  onResendEmail,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sendingId, setSendingId] = useState(null);

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return certificates;
    const term = searchTerm.toLowerCase();
    return certificates.filter((c) =>
      (c.participant_name || '').toLowerCase().includes(term) ||
      (c.email || '').toLowerCase().includes(term) ||
      (c.certificate_id || '').toLowerCase().includes(term)
    );
  }, [certificates, searchTerm]);

  const handleSingleSend = async (e, item) => {
    e.stopPropagation();
    if (!onResendEmail || sendingId) return;
    setSendingId(item.certificate_id);
    try {
      await onResendEmail(item);
    } catch {
      // Handled in parent hook
    } finally {
      setSendingId(null);
    }
  };

  const getEmailBadge = (status, error) => {
    if (!status || status === 'Not Sent') {
      return (
        <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-secondary)' }}>
          Email Not Sent
        </span>
      );
    }
    if (status === 'Sent') {
      return (
        <span className="badge badge-success">
          <Send size={11} /> Email Sent
        </span>
      );
    }
    if (status.startsWith('Failed')) {
      return (
        <span className="badge badge-danger" title={error || status}>
          <AlertCircle size={11} /> Email Failed
        </span>
      );
    }
    return (
      <span className="badge badge-warning" title={status}>
        {status}
      </span>
    );
  };

  return (
    <div className="participant-list-card">
      <div className="list-header">
        <div>
          <h4 style={{ fontSize: '15px', fontWeight: 600 }}>Participant List</h4>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {certificates.length} generated certificate(s)
          </span>
        </div>
      </div>

      <div style={{ padding: '0 16px 12px 16px' }}>
        <input
          type="text"
          className="search-input"
          placeholder="Filter by name, email, or certificate ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="participant-scroll-list">
        {filtered.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No matching participants found.
          </div>
        ) : (
          filtered.map((item, index) => {
            const isSelected = item.certificate_id === selectedId;
            const isItemSending = sendingId === item.certificate_id;

            return (
              <div
                key={item.certificate_id || index}
                className={`participant-item ${isSelected ? 'active' : ''}`}
                onClick={() => onSelectCertificate(item)}
              >
                <div>
                  <div className="part-name">
                    {index + 1}. {item.participant_name}
                  </div>
                  {item.email && (
                    <div className="part-email">
                      <Mail size={12} />
                      <span>{item.email}</span>
                    </div>
                  )}
                  <div className="part-meta">
                    ID: <strong style={{ color: 'var(--text-secondary)' }}>{item.certificate_id}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <span className={`badge ${item.status === 'Generated' ? 'badge-success' : 'badge-danger'}`}>
                      {item.status}
                    </span>
                    {getEmailBadge(item.email_status, item.email_error)}
                  </div>

                  {item.email && onResendEmail && (
                    <button
                      type="button"
                      disabled={isItemSending}
                      className="btn-secondary btn-sm"
                      style={{ padding: '3px 8px', fontSize: '11px', gap: '4px' }}
                      onClick={(e) => handleSingleSend(e, item)}
                      title={item.email_status === 'Sent' ? 'Resend certificate via Gmail SMTP' : 'Send certificate via Gmail SMTP'}
                    >
                      <RefreshCw size={11} className={isItemSending ? 'animate-spin' : ''} />
                      <span>{isItemSending ? 'Sending...' : item.email_status === 'Sent' ? 'Resend' : 'Send'}</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
