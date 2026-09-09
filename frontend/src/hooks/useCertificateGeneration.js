import { useState, useCallback } from 'react';
import { generateCertificatesApi, sendSingleEmailApi } from '../services/certificateApi';
import { SYSTEM_FIELDS } from '../components/DataMapping';

export function useCertificateGeneration() {
  const [templateFile, setTemplateFile] = useState(null);
  const [uploadedData, setUploadedData] = useState(null);
  const [mapping, setMapping] = useState({});
  const [validation, setValidation] = useState({ isValid: false, blockingErrors: [] });

  // Email delivery options
  const [sendEmails, setSendEmails] = useState(false);
  const [emailSubject, setEmailSubject] = useState('');
  const [emailStats, setEmailStats] = useState({ sent: 0, failed: 0 });

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');
  const [generationError, setGenerationError] = useState('');

  // Critical: Initially empty! No fake/demo data.
  const [generatedCertificates, setGeneratedCertificates] = useState([]);
  const [selectedCertificate, setSelectedCertificate] = useState(null);

  // Auto-match uploaded columns to system fields
  const handleDataLoaded = useCallback(({ file, fileName, records, columns }) => {
    setUploadedData({ file, fileName, records, columns });

    const newMapping = {};
    SYSTEM_FIELDS.forEach((sysField) => {
      // Find matching column in uploaded columns
      const matched = columns.find((col) => {
        const cLower = col.toLowerCase().trim();
        return sysField.synonyms.some((syn) => syn.toLowerCase() === cLower);
      });
      if (matched) {
        newMapping[sysField.key] = matched;
      }
    });

    setMapping(newMapping);
  }, []);

  const handleClearData = useCallback(() => {
    setUploadedData(null);
    setMapping({});
    setValidation({ isValid: false, blockingErrors: [] });
  }, []);

  const handleClearTemplate = useCallback(() => {
    setTemplateFile(null);
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
        const item = {};
        Object.keys(mapping).forEach((sysKey) => {
          const colName = mapping[sysKey];
          if (colName && rawRow[colName] !== undefined) {
            item[sysKey] = rawRow[colName];
          }
        });

        // Ensure certificate_id exists
        if (!item.certificate_id) {
          item.certificate_id = `CERT-${String(idx + 1).padStart(4, '0')}`;
        }
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
        format: 'png',
        sendEmails,
        emailSubject: emailSubject || undefined,
      });

      if (!response || !response.certificates || response.certificates.length === 0) {
        throw new Error('Backend did not return any generated certificates.');
      }

      setGeneratedCertificates(response.certificates);
      setSelectedCertificate(response.certificates[0]);
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
  }, [templateFile, uploadedData, mapping, validation, sendEmails, emailSubject]);

  // Resend single email
  const handleResendEmail = useCallback(async (cert) => {
    if (!cert || !cert.email) {
      throw new Error('Participant does not have an email address.');
    }
    try {
      const res = await sendSingleEmailApi({
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
  }, [emailSubject]);

  return {
    templateFile,
    setTemplateFile,
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
    emailStats,
    validation,
    setValidation,
    isGenerating,
    generationProgress,
    generationError,
    generatedCertificates,
    selectedCertificate,
    setSelectedCertificate,
    handleGenerate,
    handleResendEmail,
  };
}
