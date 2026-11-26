import { useState, useCallback, useRef } from 'react';
import {
  inspectTemplateApi,
  generateCertificatesApi,
  sendBatchEmailsApi,
  sendSingleEmailApi,
} from '../services/certificateApi';
import { SYSTEM_FIELDS } from '../components/DataMapping';

const SYSTEM_SYNONYMS_BY_KEY = SYSTEM_FIELDS.reduce((acc, field) => {
  acc[field.key] = field.synonyms || [];
  return acc;
}, {});

function normalizeMatchText(value) {
  return String(value || '')
    .replace(/^\{\{|\}\}$|^\[\[|\]\]$/g, '')
    .toLowerCase()
    .trim()
    .replace(/[\s_-]+/g, ' ');
}

function autoMatchColumns(fields, columns, previousMapping = {}) {
  if (!columns || columns.length === 0) return {};

  const activeFields = fields && fields.length > 0 ? fields : SYSTEM_FIELDS;
  const newMapping = {};

  const matchField = (field) => {
    const existing = previousMapping[field.key];
    if (existing && columns.includes(existing)) {
      return existing;
    }

    const candidates = new Set([
      normalizeMatchText(field.key),
      normalizeMatchText(field.label),
      normalizeMatchText(field.token),
      ...(SYSTEM_SYNONYMS_BY_KEY[field.key] || []).map(normalizeMatchText),
    ]);
    candidates.delete('');

    const matched = columns.find((col) => {
      const colLower = col.toLowerCase().trim();
      const colNorm = normalizeMatchText(col);
      return (
        candidates.has(colNorm) ||
        (SYSTEM_SYNONYMS_BY_KEY[field.key] || []).some((syn) => syn.toLowerCase() === colLower)
      );
    });

    return matched || '';
  };

  activeFields.forEach((field) => {
    const matched = matchField(field);
    if (matched) {
      newMapping[field.key] = matched;
    }
  });

  // Always auto-match email so bulk email delivery works even when {{email}} is not on the template
  if (!newMapping.email) {
    const emailField = SYSTEM_FIELDS.find((f) => f.key === 'email');
    if (emailField) {
      const matchedEmail = matchField(emailField);
      if (matchedEmail) {
        newMapping.email = matchedEmail;
      }
    }
  }

  return newMapping;
}

export function useCertificateGeneration() {
  const [templateFile, setTemplateFile] = useState(null);
  const [extractedPlaceholders, setExtractedPlaceholders] = useState([]);
  const [isInspectingTemplate, setIsInspectingTemplate] = useState(false);
  const [templateInspectError, setTemplateInspectError] = useState('');
  const inspectRequestIdRef = useRef(0);

  const [uploadedData, setUploadedData] = useState(null);
  const [mapping, setMapping] = useState({});
  const [validation, setValidation] = useState({ isValid: false, blockingErrors: [], warnings: [] });

  // Email & Format delivery options
  const [sendEmails, setSendEmails] = useState(false);
  const [emailSubject, setEmailSubject] = useState('');
  const [outputFormat, setOutputFormat] = useState('png'); // 'png' or 'pdf'
  const [emailStats, setEmailStats] = useState({ sent: 0, failed: 0 });
  const [isSendingBatchEmails, setIsSendingBatchEmails] = useState(false);

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');
  const [generationError, setGenerationError] = useState('');

  // Critical: Initially empty! No fake/demo data.
  const [batchId, setBatchId] = useState(null);
  const [generatedCertificates, setGeneratedCertificates] = useState([]);
  const [selectedCertificate, setSelectedCertificate] = useState(null);

  // Inspect uploaded template for dynamic placeholders & styles
  const handleTemplateSelected = useCallback(
    async (file) => {
      setTemplateFile(file || null);
      setTemplateInspectError('');

      if (!file) {
        setExtractedPlaceholders([]);
        setIsInspectingTemplate(false);
        return;
      }

      const requestId = ++inspectRequestIdRef.current;
      setIsInspectingTemplate(true);

      let nextPlaceholders = SYSTEM_FIELDS;
      try {
        const res = await inspectTemplateApi(file);
        if (requestId !== inspectRequestIdRef.current) return;

        const detected = Array.isArray(res?.extracted_placeholders) ? res.extracted_placeholders : [];
        if (detected.length > 0) {
          nextPlaceholders = detected;
        } else {
          nextPlaceholders = SYSTEM_FIELDS;
        }
      } catch (err) {
        if (requestId !== inspectRequestIdRef.current) return;
        setTemplateInspectError(err.message || 'Template inspection unavailable; using default fields.');
        nextPlaceholders = SYSTEM_FIELDS;
      } finally {
        if (requestId === inspectRequestIdRef.current) {
          setIsInspectingTemplate(false);
        }
      }

      if (requestId !== inspectRequestIdRef.current) return;
      setExtractedPlaceholders(nextPlaceholders);

      if (uploadedData?.columns?.length > 0) {
        setMapping((prev) => autoMatchColumns(nextPlaceholders, uploadedData.columns, prev));
      }
    },
    [uploadedData]
  );

  // Auto-match uploaded columns to extracted placeholders / system fields
  const handleDataLoaded = useCallback(
    ({ file, fileName, records, columns }) => {
      setUploadedData({ file, fileName, records, columns });
      const activeFields = extractedPlaceholders.length > 0 ? extractedPlaceholders : SYSTEM_FIELDS;
      setMapping(autoMatchColumns(activeFields, columns));
    },
    [extractedPlaceholders]
  );

  const handleClearData = useCallback(() => {
    setUploadedData(null);
    setMapping({});
    setValidation({ isValid: false, blockingErrors: [] });
  }, []);

  const handleClearTemplate = useCallback(() => {
    inspectRequestIdRef.current += 1;
    setTemplateFile(null);
    setExtractedPlaceholders([]);
    setIsInspectingTemplate(false);
    setTemplateInspectError('');
  }, []);

  // Execute batch certificate generation
  const handleGenerate = useCallback(async () => {
    if (!templateFile || !uploadedData || !validation.isValid) return;

    setIsGenerating(true);
    setGenerationError('');
    setGenerationProgress(`Preparing ${uploadedData.records.length} records...`);

    try {
      // Map participant records according to user mapping
      const mappedParticipants = uploadedData.records.map((rawRow, idx) => {
        const item = {
          // Auto-generated Certificate ID
          certificate_id: `CERT-${String(idx + 1).padStart(4, '0')}`,
        };

        Object.keys(mapping).forEach((sysKey) => {
          const colName = mapping[sysKey];
          if (colName && rawRow[colName] !== undefined) {
            item[sysKey] = rawRow[colName];
          }
        });

        return item;
      });

      setGenerationProgress(
        sendEmails
          ? `Generating ${mappedParticipants.length} certificate(s) & dispatching emails via Gmail SMTP...`
          : `Generating ${mappedParticipants.length} certificate(s) via backend engine...`
      );

      const response = await generateCertificatesApi({
        templateFile,
        participants: mappedParticipants,
        format: outputFormat,
        sendEmails,
        emailSubject: emailSubject || undefined,
        fieldMapping: mapping,
      });

      if (!response || !response.certificates || response.certificates.length === 0) {
        throw new Error('Backend did not return any generated certificates.');
      }

      setBatchId(response.batch_id || null);

      const normalizedCertificates = response.certificates.map((cert) => ({
        ...cert,
        preview_url:
          cert.preview_url ||
          (cert.filename
            ? response.batch_id
              ? `/api/certificates/download/${response.batch_id}/${cert.filename}`
              : `/api/certificates/download/${cert.filename}`
            : ''),
      }));

      setGeneratedCertificates(normalizedCertificates);
      setSelectedCertificate(normalizedCertificates[0]);
      setEmailStats({
        sent: response.emails_sent_count || 0,
        failed: response.emails_failed_count || 0,
      });
      setIsGenerating(false);
      setGenerationProgress('');
    } catch (err) {
      setIsGenerating(false);
      setGenerationProgress('');
      setGenerationError(err.message || 'Certificate generation failed. Please check your uploaded data and try again.');
    }
  }, [templateFile, uploadedData, mapping, validation, sendEmails, emailSubject, outputFormat]);

  // Dispatch bulk emails after reviewing generated certificates and any overflow warnings
  const handleSendBatchEmails = useCallback(
    async (overrideSubject) => {
      const eligible = generatedCertificates.filter(
        (c) => c.status === 'Generated' && c.email && c.filename && c.email_status !== 'Sent'
      );

      if (eligible.length === 0) {
        throw new Error('No pending generated certificates with recipient email addresses to send.');
      }

      setIsSendingBatchEmails(true);
      try {
        const res = await sendBatchEmailsApi({
          batch_id: batchId || undefined,
          filenames: eligible.map((c) => c.filename),
          recipients: eligible.map((c) => ({
            ...(c.item_data || {}),
            certificate_id: c.certificate_id,
            filename: c.filename,
            email: c.email,
            full_name: c.participant_name,
            achievement_title: c.achievement_title || '',
            issue_date: c.issue_date || '',
          })),
          subject: (overrideSubject ?? emailSubject) || undefined,
        });

        const results = Array.isArray(res?.results) ? res.results : [];
        const byCertId = new Map();
        const byEmail = new Map();
        results.forEach((r) => {
          if (r.certificate_id) byCertId.set(r.certificate_id, r);
          if (r.email) byEmail.set(r.email, r);
        });

        setGeneratedCertificates((prev) => {
          const updated = prev.map((c) => {
            const match = byCertId.get(c.certificate_id) || byEmail.get(c.email);
            if (!match) return c;
            return {
              ...c,
              email_status: match.status,
              email_error: match.error || null,
            };
          });

          const sentCount = updated.filter((c) => c.email_status === 'Sent').length;
          const failedCount = updated.filter((c) => c.email_status?.startsWith('Failed')).length;
          setEmailStats({ sent: sentCount, failed: failedCount });

          return updated;
        });

        setSelectedCertificate((prev) => {
          if (!prev) return prev;
          const match = byCertId.get(prev.certificate_id) || byEmail.get(prev.email);
          if (!match) return prev;
          return { ...prev, email_status: match.status, email_error: match.error || null };
        });

        return res;
      } finally {
        setIsSendingBatchEmails(false);
      }
    },
    [generatedCertificates, batchId, emailSubject]
  );

  // Resend single email
  const handleResendEmail = useCallback(async (cert) => {
    if (!cert || !cert.email) {
      throw new Error('Participant does not have an email address.');
    }
    try {
      const res = await sendSingleEmailApi({
        batch_id: batchId || cert.batch_id || undefined,
        filename: cert.filename,
        email: cert.email,
        full_name: cert.participant_name,
        certificate_id: cert.certificate_id,
        achievement_title: cert.achievement_title || '',
        issue_date: cert.issue_date || '',
        subject: emailSubject || undefined,
      });

      setGeneratedCertificates((prev) =>
        prev.map((c) =>
          c.certificate_id === cert.certificate_id
            ? { ...c, email_status: res.status, email_error: res.error || null }
            : c
        )
      );

      setSelectedCertificate((prev) => {
        if (prev && prev.certificate_id === cert.certificate_id) {
          return { ...prev, email_status: res.status, email_error: res.error || null };
        }
        return prev;
      });

      return res;
    } catch (err) {
      const errorMsg = err.message || 'Email dispatch failed';
      setGeneratedCertificates((prev) =>
        prev.map((c) =>
          c.certificate_id === cert.certificate_id
            ? { ...c, email_status: `Failed: ${errorMsg}`, email_error: errorMsg }
            : c
        )
      );
      throw err;
    }
  }, [batchId, emailSubject]);

  return {
    templateFile,
    setTemplateFile,
    handleTemplateSelected,
    extractedPlaceholders,
    isInspectingTemplate,
    templateInspectError,
    uploadedData,
    handleDataLoaded,
    handleClearData,
    handleClearTemplate,
    mapping,
    setMapping,
    sendEmails,
    setSendEmails,
    emailSubject,
    setEmailSubject,
    outputFormat,
    setOutputFormat,
    emailStats,
    isSendingBatchEmails,
    validation,
    setValidation,
    isGenerating,
    generationProgress,
    generationError,
    batchId,
    generatedCertificates,
    selectedCertificate,
    setSelectedCertificate,
    handleGenerate,
    handleSendBatchEmails,
    handleResendEmail,
  };
}
