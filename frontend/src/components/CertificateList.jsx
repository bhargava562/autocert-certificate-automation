import React, { useState, useMemo } from 'react';
import { Search, Mail, ShieldCheck, User } from 'lucide-react';

export default function CertificateList({
  certificates = [],
  selectedId,
  onSelectCertificate
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return certificates;
    const term = searchTerm.toLowerCase();
    return certificates.filter((c) =>
      (c.participant_name || '').toLowerCase().includes(term) ||
      (c.email || '').toLowerCase().includes(term) ||
      (c.certificate_id || '').toLowerCase().includes(term)
    );
  }, [certificates, searchTerm]);

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

                <div>
                  <span className={`badge ${item.status === 'Generated' ? 'badge-success' : 'badge-danger'}`}>
                    {item.status}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
