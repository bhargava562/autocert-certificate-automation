import React, { useState, useMemo } from 'react';
import { Mail, Send, AlertCircle, AlertTriangle, RefreshCw } from 'lucide-react';

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

  const overflowCount = useMemo(
    () =>
      certificates.filter(
        (c) => c.overflowed || (Array.isArray(c.warnings) && c.warnings.length > 0)
      ).length,
    [certificates]
  );

  return (
    <div className="participant-list-card">
      <div className="list-header">
        <div>
          <h4 style={{ fontSize: '15px', fontWeight: 600 }}>Participant List</h4>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {certificates.length} generated certificate(s)
            {overflowCount > 0 && (
              <span style={{ color: '#fbbf24', marginLeft: '8px', fontWeight: 600 }}>
                • {overflowCount} with warning(s)
              </span>
            )}
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
            const itemWarnings = Array.isArray(item.warnings) ? item.warnings : [];
            const hasOverflow = Boolean(item.overflowed);
            const hasWarnings = hasOverflow || itemWarnings.length > 0;
            const warningTitle = itemWarnings.length > 0
              ? itemWarnings.join(' | ')
              : 'Text exceeded template bounding box';

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
                  {hasWarnings && (
                    <div
                      style={{
                        marginTop: '4px',
                        fontSize: '11px',
                        color: '#fbbf24',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                      title={warningTitle}
                    >
                      <AlertTriangle size={11} />
                      <span>
                        {itemWarnings[0] || 'Text overflow detected'}
                      </span>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '6px' }}>
                    <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                      {item.filename?.toLowerCase().endsWith('.pdf') ? 'PDF' : 'PNG'}
                    </span>
                    <span className={`badge ${item.status === 'Generated' ? 'badge-success' : 'badge-danger'}`}>
                      {item.status}
                    </span>
                    {hasWarnings && (
                      <span className="badge badge-warning" title={warningTitle}>
                        <AlertTriangle size={11} />
                        {hasOverflow ? 'Overflow' : `${itemWarnings.length} Warning${itemWarnings.length > 1 ? 's' : ''}`}
                      </span>
                    )}
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
