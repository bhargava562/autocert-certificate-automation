import React from 'react';
import { Check, AlertTriangle, XCircle } from 'lucide-react';

export const SYSTEM_FIELDS = [
  { key: 'full_name', label: 'Recipient Name', required: true, synonyms: ['full_name', 'name', 'recipient_name', 'participant_name', 'student_name'] },
  { key: 'certificate_id', label: 'Certificate ID', required: true, synonyms: ['certificate_id', 'cert_id', 'id', 'registration_id'] },
  { key: 'email', label: 'Email ID', required: false, synonyms: ['email', 'email_address', 'mail', 'participant_email'] },
  { key: 'achievement_title', label: 'Achievement Title', required: false, synonyms: ['achievement_title', 'role', 'event_name', 'course_title', 'title'] },
  { key: 'achievement_text', label: 'Achievement Text', required: false, synonyms: ['achievement_text', 'description', 'citation'] },
  { key: 'issue_date', label: 'Issue Date', required: false, synonyms: ['issue_date', 'date', 'participated_date', 'awarded_date'] },
  { key: 'organization_on_certificate', label: 'Organization', required: false, synonyms: ['organization_on_certificate', 'organization', 'company', 'org'] },
  { key: 'signer_name', label: 'Signer Name', required: false, synonyms: ['signer_name', 'authorized_by', 'director', 'signature_name'] },
  { key: 'signer_title', label: 'Signer Title', required: false, synonyms: ['signer_title', 'designation', 'signer_role'] },
];

export default function DataMapping({ columns = [], mapping = {}, onMappingChange }) {
  const handleSelectChange = (systemKey, selectedColumn) => {
    onMappingChange({
      ...mapping,
      [systemKey]: selectedColumn,
    });
  };

  return (
    <div className="mapping-section">
      <div className="mapping-header">
        <h4 className="mapping-title">Data Field Mapping</h4>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Map columns from your uploaded dataset to certificate system fields
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
          } else if (field.required) {
            badge = (
              <span className="badge badge-danger">
                <XCircle size={12} /> Required
              </span>
            );
          } else {
            badge = (
              <span className="badge badge-warning">
                <AlertTriangle size={12} /> Missing
              </span>
            );
          }

          return (
            <div key={field.key} className="mapping-row">
              <div className="mapping-label">
                <span>
                  {field.label} {field.required && <strong style={{ color: '#f87171' }}>*</strong>}
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
    </div>
  );
}
