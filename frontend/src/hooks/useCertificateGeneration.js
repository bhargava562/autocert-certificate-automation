import { useState, useCallback, useRef } from 'react';
import { generateCertificatesApi, sendSingleEmailApi, inspectTemplateApi } from '../services/certificateApi';
import { SYSTEM_FIELDS } from '../components/DataMapping';

export function findBestMatchingColumn(targetKey, columns = []) {
  if (!columns || columns.length === 0 || !targetKey) return '';
  const normKey = targetKey.toLowerCase().replace(/[^a-z0-9]/g, '');

  const keywordMap = {
    name: ['studentname', 'fullname', 'recipientname', 'participantname', 'candidatename', 'nameasper', 'name'],
    fullname: ['studentname', 'fullname', 'recipientname', 'participantname', 'candidatename', 'nameasper', 'name'],
    email: ['emailaddress', 'collegeemail', 'emailid', 'mailid', 'email', 'mail'],
    year: ['academicyear', 'studyyear', 'classyear', 'yearofstudy', 'year'],
    dept: ['department', 'dept', 'branch', 'discipline', 'stream'],
    department: ['department', 'dept', 'branch', 'discipline', 'stream'],
    certificateid: ['collegeregisternumber', 'registernumber', 'regno', 'rollnumber', 'studentid', 'certid', 'certificateid', 'registrationid', 'idnumber', 'register', 'roll', 'id'],
    eventname: ['eventname', 'workshopname', 'programname', 'coursename', 'event', 'workshop', 'program', 'course'],
    achievementtitle: ['role', 'specialization', 'achievementtitle', 'eventname', 'coursename', 'title'],
    achievementtext: ['achievementtext', 'citation', 'description'],
    issuedate: ['issuedate', 'participateddate', 'awarddate', 'date']
  };

  const keywords = keywordMap[normKey] || [normKey];

  // Exact normalized equality
  for (const kw of keywords) {
    for (const col of columns) {
      const normCol = col.toLowerCase().replace(/[^a-z0-9]/g, '');
      if (normCol === kw) return col;
    }
  }

  // Substring inclusion
  for (const kw of keywords) {
    for (const col of columns) {
      const normCol = col.toLowerCase().replace(/[^a-z0-9]/g, '');
      if (normCol.includes(kw)) return col;
    }
  }

  // Token matching
  for (const col of columns) {
    const tokens = col.toLowerCase().split(/[^a-z0-9]+/);
    for (const kw of keywords) {
      if (tokens.includes(kw)) return col;
    }
  }

  return '';
}

export function useCertificateGeneration() {
  const [templateFile, setTemplateFile] = useState(null);
  const [templatePlaceholders, setTemplatePlaceholders] = useState([]);
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

  // Synchronization refs to eliminate any upload order race condition
  const placeholdersRef = useRef([]);
  const uploadedDataRef = useRef(null);

  // Auto-calculate best field mapping based on current template placeholders & uploaded columns
  const computeAutoMapping = useCallback((placeholders, columns) => {
    if (!columns || columns.length === 0) return {};
    const newMapping = {};

    if (placeholders && placeholders.length > 0) {
      // Map detected PDF placeholders
      placeholders.forEach((pKey) => {
        const matched = findBestMatchingColumn(pKey, columns);
        if (matched) newMapping[pKey] = matched;
      });
      // Always also map email and certificate_id for dispatch & identification
      const emailCol = findBestMatchingColumn('email', columns);
      if (emailCol) newMapping.email = emailCol;

      const idCol = findBestMatchingColumn('certificate_id', columns);
      if (idCol) newMapping.certificate_id = idCol;
    } else {
      // Standard system fields
      SYSTEM_FIELDS.forEach((sysField) => {
        const matched = findBestMatchingColumn(sysField.key, columns);
        if (matched) newMapping[sysField.key] = matched;
      });
    }

    return newMapping;
  }, []);

  // Quick client-side scan for {{placeholder}} tokens in vector PDF files
  const extractPlaceholdersClientSide = async (file) => {
    try {
      const text = await file.text();
      const matches = text.match(/\{\{\s*([a-zA-Z0-9_\s-]+?)\s*\}\}/g);
      if (matches && matches.length > 0) {
        const extracted = matches.map((m) =>
          m.replace(/^\{\{\s*/, '').replace(/\s*\}\}$/, '').trim()
        );
        return Array.from(new Set(extracted.filter(Boolean)));
      }
    } catch {
      // Fallback to server inspection
    }
    return [];
  };

  // Template uploaded or changed
  const handleTemplateSelected = useCallback(async (file) => {
    setTemplateFile(file);
    if (!file) {
      placeholdersRef.current = [];
      setTemplatePlaceholders([]);
      return;
    }

    const isPdf = file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
    let currentPlaceholders = [];

    // Step 1: Instant client-side inspection for zero-latency UI response
    if (isPdf) {
      const clientExtracted = await extractPlaceholdersClientSide(file);
      if (clientExtracted.length > 0) {
        currentPlaceholders = clientExtracted;
        placeholdersRef.current = clientExtracted;
        setTemplatePlaceholders(clientExtracted);

        if (uploadedDataRef.current?.columns) {
          const newMapping = computeAutoMapping(clientExtracted, uploadedDataRef.current.columns);
          setMapping(newMapping);
        }
      }
    }

    // Step 2: Backend inspection to confirm and extract styling details
    try {
      const insp = await inspectTemplateApi(file);
      if (insp.has_placeholders && Array.isArray(insp.placeholders) && insp.placeholders.length > 0) {
        currentPlaceholders = insp.placeholders;
        placeholdersRef.current = insp.placeholders;
        setTemplatePlaceholders(insp.placeholders);

        if (uploadedDataRef.current?.columns) {
          const newMapping = computeAutoMapping(insp.placeholders, uploadedDataRef.current.columns);
          setMapping(newMapping);
        }
      }
    } catch {
      // If backend inspection has a temporary network error, client-extracted placeholders remain active
    }
  }, [computeAutoMapping]);

  // Data loaded (CSV / JSON / XLSX)
  const handleDataLoaded = useCallback(({ file, fileName, records, columns }) => {
    uploadedDataRef.current = { file, fileName, records, columns };
    setUploadedData({ file, fileName, records, columns });

    const currentPlaceholders = placeholdersRef.current || [];
    const newMapping = computeAutoMapping(currentPlaceholders, columns);
    setMapping(newMapping);
  }, [computeAutoMapping]);

  const handleClearData = useCallback(() => {
    uploadedDataRef.current = null;
    setUploadedData(null);
    setMapping({});
    setValidation({ isValid: false, blockingErrors: [] });
  }, []);

  const handleClearTemplate = useCallback(() => {
    placeholdersRef.current = [];
    setTemplateFile(null);
    setTemplatePlaceholders([]);
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

        // Synchronize name and full_name so both placeholders and system fields work
        if (item.name && !item.full_name) item.full_name = item.name;
        if (item.full_name && !item.name) item.name = item.full_name;

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
    templatePlaceholders,
    handleTemplateSelected,
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
