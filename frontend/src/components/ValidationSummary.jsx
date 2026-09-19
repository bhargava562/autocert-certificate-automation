import React, { useMemo, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { SYSTEM_FIELDS } from './DataMapping';

export default function ValidationSummary({ records = [], mapping = {}, sendEmails = false, onValidationChange }) {
  const validationResult = useMemo(() => {
    if (!records || records.length === 0) {
      return {
        total: 0,
        validCount: 0,
        warningCount: 0,
        duplicateIdCount: 0,
        missingRequiredFields: false,
        blockingErrors: ['No data records loaded.'],
        isValid: false,
      };
    }

    const nameCol = mapping['full_name'];
    const emailCol = mapping['email'];

    const blockingErrors = [];
    if (!nameCol) {
      blockingErrors.push('Recipient Name column is not mapped.');
    }
    if (sendEmails && !emailCol) {
      blockingErrors.push('Recipient Email column must be mapped to dispatch emails via Gmail SMTP.');
    }

    let validCount = 0;
    let warningCount = 0;

    records.forEach((row) => {
      const nameVal = nameCol ? String(row[nameCol] || '').trim() : '';
      const emailVal = emailCol ? String(row[emailCol] || '').trim() : '';

      let hasWarning = false;
      let hasError = false;

      if (!nameVal) {
        hasError = true;
      }

      // Check email format if provided
      if (emailVal && !emailVal.includes('@')) {
        hasWarning = true;
      }

      // Check if optional certificate details are missing
      if (!row[mapping['achievement_text']] && !row[mapping['achievement_title']]) {
        hasWarning = true;
      }

      if (!hasError) {
        validCount++;
        if (hasWarning) {
          warningCount++;
        }
      }
    });

    const isValid = blockingErrors.length === 0 && validCount > 0;

    return {
      total: records.length,
      validCount,
      warningCount,
      duplicateIdCount: 0,
      blockingErrors,
      isValid,
    };
  }, [records, mapping, sendEmails]);

  useEffect(() => {
    onValidationChange(validationResult);
  }, [validationResult, onValidationChange]);

  return (
    <div className="validation-summary">
      <div className="val-item val-valid">
        <CheckCircle2 size={18} />
        <span>{validationResult.validCount} valid records</span>
      </div>

      {validationResult.warningCount > 0 && (
        <div className="val-item val-warning">
          <AlertTriangle size={18} />
          <span>{validationResult.warningCount} records need attention</span>
        </div>
      )}

      {validationResult.duplicateIdCount > 0 && (
        <div className="val-item val-error">
          <XCircle size={18} />
          <span>{validationResult.duplicateIdCount} duplicate certificate ID(s)</span>
        </div>
      )}

      {validationResult.blockingErrors.length > 0 && (
        <div style={{ width: '100%', marginTop: '8px', color: '#f87171', fontSize: '12px' }}>
          {validationResult.blockingErrors.map((err, i) => (
            <div key={i}>• {err}</div>
          ))}
        </div>
      )}
    </div>
  );
}
