import React from 'react';
import { Check, AlertTriangle, XCircle, Mail, Send, Loader2 } from 'lucide-react';

export const SYSTEM_FIELDS = [
  { key: 'full_name', label: 'Recipient Name', required: true, synonyms: ['full_name', 'name', 'recipient_name', 'participant_name', 'student_name', 'student name (as per college id card)', 'student name'] },
  { key: 'email', label: 'Recipient Email', required: false, synonyms: ['email', 'email_address', 'mail', 'email address', 'participant_email', 'recipient_email', 'college email id (do not give personal email)'] },
  { key: 'year', label: 'Year / Class', required: false, synonyms: ['year', 'academic_year', 'batch_year', 'class', 'grade'] },
  { key: 'department', label: 'Department / Branch', required: false, synonyms: ['department', 'dept', 'branch', 'stream', 'major', 'field'] },
  { key: 'achievement_title', label: 'Achievement Title', required: false, synonyms: ['achievement_title', 'role', 'event_name', 'course_title', 'title'] },
  { key: 'achievement_text', label: 'Achievement Text', required: false, synonyms: ['achievement_text', 'description', 'citation'] },
];

export default function DataMapping({
  columns = [],
  mapping = {},
  onMappingChange,
  placeholders = [],
  isInspectingTemplate = false,
  sendEmails = false,
  onSendEmailsChange,
  emailSubject = '',
  onEmailSubjectChange,
  outputFormat = 'png',
  onOutputFormatChange,
}) {
  const handleSelectChange = (systemKey, selectedColumn) => {
    onMappingChange({
      ...mapping,
      [systemKey]: selectedColumn,
    });
  };

  const fieldsToRender = placeholders && placeholders.length > 0 ? placeholders : SYSTEM_FIELDS;
  const hasEmailInFields = fieldsToRender.some((f) => f.key === 'email');
  const isEmailMapped = Boolean(mapping.email && mapping.email !== '');

  return (
    <div className="mapping-section">
      <div className="mapping-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <h4 className="mapping-title">Dataset Column Mapping</h4>
          {isInspectingTemplate && (
            <span style={{ fontSize: '12px', color: '#38bdf8', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <Loader2 size={13} className="spin" /> Inspecting template...
            </span>
          )}
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Map detected template placeholders to columns from your uploaded dataset (Certificate IDs are auto-assigned)
        </span>
      </div>

      <div className="mapping-grid">
        {fieldsToRender.map((field) => {
          const mappedCol = mapping[field.key];
          const isMapped = Boolean(mappedCol && mappedCol !== '');
          const isRequired = Boolean(field.required || (field.key === 'email' && sendEmails));

          let badge = null;
          if (isMapped) {
            badge = (
              <span className="badge badge-success">
                <Check size={12} /> Mapped
              </span>
            );
          } else if (isRequired) {
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
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  {field.key === 'email' && <Mail size={13} color="#10b981" />}
                  <span>{field.label || field.key}</span>
                  {isRequired && <strong style={{ color: '#f87171' }}>*</strong>}
                  {field.token && (
                    <code
                      style={{
                        fontSize: '11px',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: 'rgba(255, 255, 255, 0.07)',
                        color: '#93c5fd',
                      }}
                    >
                      {field.token}
                    </code>
                  )}
                  {field.bold && (
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: 'rgba(139, 92, 246, 0.16)',
                        color: '#c4b5fd',
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                      }}
                    >
                      Bold
                    </span>
                  )}
                  {field.italic && (
                    <span
                      style={{
                        fontSize: '10px',
                        fontStyle: 'italic',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: 'rgba(59, 130, 246, 0.16)',
                        color: '#93c5fd',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                      }}
                    >
                      Italic
                    </span>
                  )}
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

      {/* Output Format Selector Card */}
      <div
        style={{
          marginTop: '20px',
          padding: '16px',
          background: 'rgba(59, 130, 246, 0.04)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div>
          <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Target Output Format</span>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Choose whether to generate in-browser PNG images or printable vector PDF documents
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={outputFormat === 'png' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => onOutputFormatChange && onOutputFormatChange('png')}
            style={{ fontWeight: 600 }}
          >
            <span>PNG Images (.png)</span>
          </button>
          <button
            type="button"
            className={outputFormat === 'pdf' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => onOutputFormatChange && onOutputFormatChange('pdf')}
            style={{ fontWeight: 600 }}
          >
            <span>PDF Documents (.pdf)</span>
          </button>
        </div>
      </div>

      {/* Bulk Email Delivery Configuration Card */}
      <div
        style={{
          marginTop: '14px',
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
          <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {!hasEmailInFields && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Mail size={13} color="#10b981" />
                  <span>Recipient Email Column <strong style={{ color: '#f87171' }}>*</strong></span>
                </label>
                <select
                  className="mapping-select"
                  value={mapping.email || ''}
                  onChange={(e) => handleSelectChange('email', e.target.value)}
                >
                  <option value="">-- Select uploaded email column --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>
            )}

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

