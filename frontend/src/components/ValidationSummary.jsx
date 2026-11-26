import React, { useMemo, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

export default function ValidationSummary({
  records = [],
  mapping = {},
  placeholders = [],
  sendEmails = false,
  onValidationChange,
}) {
  const validationResult = useMemo(() => {
    if (!records || records.length === 0) {
      return {
        total: 0,
        validCount: 0,
        warningCount: 0,
        duplicateIdCount: 0,
        missingRequiredFields: false,
        blockingErrors: ['No data records loaded.'],
        warnings: [],
        isValid: false,
      };
    }

    const activeFields = placeholders && placeholders.length > 0 ? placeholders : [];
    const explicitRequired = activeFields.filter((f) => f.required);
    const requiredFields =
      explicitRequired.length > 0
        ? explicitRequired
        : activeFields.length > 0
          ? activeFields.filter((f) => f.key === 'full_name')
          : [{ key: 'full_name', label: 'Recipient Name', required: true }];

    const primaryField = requiredFields[0] || activeFields[0] || { key: 'full_name', label: 'Recipient Name' };
    const primaryCol = mapping[primaryField.key];
    const emailCol = mapping['email'];

    const blockingErrors = [];
    const warnings = [];

    if (requiredFields.length > 0) {
      requiredFields.forEach((reqField) => {
        if (!mapping[reqField.key]) {
          blockingErrors.push(`${reqField.label || reqField.key} column is not mapped.`);
        }
      });
    } else if (!Object.values(mapping).some(Boolean)) {
      blockingErrors.push('At least one template placeholder column must be mapped.');
    }

    if (sendEmails && !emailCol) {
      blockingErrors.push('Recipient Email column must be mapped to dispatch emails via Gmail SMTP.');
    }

    let validCount = 0;
    let warningCount = 0;
    let missingPrimaryCount = 0;
    let invalidEmailCount = 0;
    let missingOptionalCount = 0;

    const optionalMappedKeys = (activeFields.length > 0
      ? activeFields
          .filter((f) => f.key !== primaryField.key && f.key !== 'email' && mapping[f.key])
          .map((f) => f.key)
      : ['achievement_text', 'achievement_title'].filter((k) => mapping[k]));

    records.forEach((row) => {
      const primaryVal = primaryCol ? String(row[primaryCol] || '').trim() : '';
      const emailVal = emailCol ? String(row[emailCol] || '').trim() : '';

      let hasWarning = false;
      let hasError = false;

      if (primaryCol && !primaryVal) {
        hasError = true;
        missingPrimaryCount++;
      }

      // Check email format if provided
      if (emailVal && !emailVal.includes('@')) {
        hasWarning = true;
        invalidEmailCount++;
      }

      // Check if optional mapped certificate details are missing
      if (
        optionalMappedKeys.length > 0 &&
        optionalMappedKeys.every((key) => !String(row[mapping[key]] || '').trim())
      ) {
        hasWarning = true;
        missingOptionalCount++;
      }

      if (!hasError) {
        validCount++;
        if (hasWarning) {
          warningCount++;
        }
      }
    });

    if (primaryCol && validCount === 0) {
      blockingErrors.push(`No records contain a valid ${primaryField.label || primaryField.key}.`);
    }

    if (missingPrimaryCount > 0 && validCount > 0) {
      warnings.push(`${missingPrimaryCount} record(s) are missing ${primaryField.label || primaryField.key} and will be skipped.`);
    }
    if (invalidEmailCount > 0) {
      warnings.push(`${invalidEmailCount} record(s) have an invalid email address format.`);
    }
    if (missingOptionalCount > 0) {
      warnings.push(`${missingOptionalCount} record(s) are missing optional mapped placeholder details.`);
    }

    const isValid = blockingErrors.length === 0 && validCount > 0;

    return {
      total: records.length,
      validCount,
      warningCount,
      duplicateIdCount: 0,
      blockingErrors,
      warnings,
      isValid,
    };
  }, [records, mapping, placeholders, sendEmails]);

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
          <span>{validationResult.warningCount} records have non-blocking warnings</span>
        </div>
      )}

      {validationResult.duplicateIdCount > 0 && (
        <div className="val-item val-error">
          <XCircle size={18} />
          <span>{validationResult.duplicateIdCount} duplicate certificate ID(s)</span>
        </div>
      )}

      {validationResult.blockingErrors.length > 0 && (
        <div
          role="alert"
          style={{
            width: '100%',
            marginTop: '8px',
            padding: '10px 12px',
            borderRadius: '6px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: '12px',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <XCircle size={14} />
            <span>Blocking Errors (must fix before generating)</span>
          </div>
          {validationResult.blockingErrors.map((err, i) => (
            <div key={i}>• {err}</div>
          ))}
        </div>
      )}

      {validationResult.warnings.length > 0 && (
        <div
          style={{
            width: '100%',
            marginTop: '8px',
            padding: '10px 12px',
            borderRadius: '6px',
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#fbbf24',
            fontSize: '12px',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={14} />
            <span>Warnings (non-blocking — generation allowed)</span>
          </div>
          {validationResult.warnings.map((warn, i) => (
            <div key={i}>• {warn}</div>
          ))}
        </div>
      )}
    </div>
  );
}
