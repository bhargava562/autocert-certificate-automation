import React from 'react';
import { Check, AlertTriangle, XCircle, Mail, Send, Sparkles } from 'lucide-react';

export const SYSTEM_FIELDS = [
  { key: 'full_name', label: 'Recipient Name', required: true, synonyms: ['full_name', 'name', 'recipient_name', 'participant_name', 'student_name'] },
  { key: 'certificate_id', label: 'Certificate ID', required: true, synonyms: ['certificate_id', 'cert_id', 'id', 'registration_id'] },
  { key: 'email', label: 'Recipient Email', required: false, synonyms: ['email', 'email_address', 'mail', 'participant_email', 'recipient_email'] },
  { key: 'achievement_title', label: 'Achievement Title', required: false, synonyms: ['achievement_title', 'role', 'event_name', 'course_title', 'title'] },
  { key: 'achievement_text', label: 'Achievement Text', required: false, synonyms: ['achievement_text', 'description', 'citation'] },
  { key: 'issue_date', label: 'Issue Date', required: false, synonyms: ['issue_date', 'date', 'participated_date', 'awarded_date'] },
  { key: 'organization_on_certificate', label: 'Organization', required: false, synonyms: ['organization_on_certificate', 'organization', 'company', 'org'] },
  { key: 'signer_name', label: 'Signer Name', required: false, synonyms: ['signer_name', 'authorized_by', 'director', 'signature_name'] },
  { key: 'signer_title', label: 'Signer Title', required: false, synonyms: ['signer_title', 'designation', 'signer_role'] },
];

export default function DataMapping({
  columns = [],
  mapping = {},
  onMappingChange,
  sendEmails = false,
  onSendEmailsChange,
  emailSubject = '',
  onEmailSubjectChange,
}) {
  const handleSelectChange = (systemKey, selectedColumn) => {
    onMappingChange({
      ...mapping,
      [systemKey]: selectedColumn,
    });
  };

  const isEmailMapped = Boolean(mapping.email && mapping.email !== '');

  return (
    <div className="mapping-section">
      <div className="mapping-header">
        <h4 className="mapping-title">Data Field Mapping</h4>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Map columns from your uploaded dataset to certificate template and dispatch fields
        </span>
      </div>

      <div className="mapping-grid">
        {SYSTEM_FIELDS.map((field) => {
          const mappedCol = mapping[field.key];
          const isMapped = Boolean(mappedCol && mappedCol !== '');

          let badge = null;
          if (isMapped) {
            badge = (
              <span className="badge badge-success">
                <Check size={12} /> Mapped
              </span>
            );
          } else if (field.required || (field.key === 'email' && sendEmails)) {
            badge = (
              <span className="badge badge-danger">
                <XCircle size={12} /> {field.key === 'email' ? 'Required for Email' : 'Required'}
              </span>
            );
          } else {
            badge = (
              <span className="badge badge-warning">
                <AlertTriangle size={12} /> Optional
              </span>
            );
          }

          return (
            <div
              key={field.key}
              className="mapping-row"
              style={field.key === 'email' && sendEmails && !isMapped ? { borderColor: 'rgba(239, 68, 68, 0.4)' } : {}}
            >
              <div className="mapping-label">
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {field.key === 'email' && <Mail size={13} color="#10b981" />}
                  {field.label} {(field.required || (field.key === 'email' && sendEmails)) && <strong style={{ color: '#f87171' }}>*</strong>}
                </span>
                {badge}
              </div>

              <select
                className="mapping-select"
                value={mappedCol || ''}
                onChange={(e) => handleSelectChange(field.key, e.target.value)}
              >
                <option value="">-- Select uploaded column --</option>
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>

      {/* Bulk Email Delivery Configuration Card */}
      <div
        style={{
          marginTop: '20px',
          padding: '16px',
          background: 'rgba(16, 185, 129, 0.04)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}>
            <input
              type="checkbox"
              checked={sendEmails}
              onChange={(e) => onSendEmailsChange && onSendEmailsChange(e.target.checked)}
              style={{ width: '16px', height: '16px', accentColor: 'var(--accent-primary)', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Send size={15} color="var(--accent-primary)" />
              <span>Send Bulk Emails with Attached Certificate via Gmail SMTP</span>
            </div>
          </label>

          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Sequential rate-limited dispatch (0.15s pacing) & per-recipient error isolation
          </span>
        </div>

        {sendEmails && (
          <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Email Subject Line (Optional — defaults to official certificate subject):
              </label>
              <input
                type="text"
                placeholder="e.g. Your Certificate of Appreciation is Ready!"
                value={emailSubject}
                onChange={(e) => onEmailSubjectChange && onEmailSubjectChange(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)',
                  padding: '8px 12px',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>

            {!isEmailMapped && (
              <div
                style={{
                  marginTop: '10px',
                  fontSize: '12px',
                  color: '#f87171',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <AlertTriangle size={14} />
                <span>Please map the <strong>Recipient Email</strong> column above to enable automated email delivery.</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
