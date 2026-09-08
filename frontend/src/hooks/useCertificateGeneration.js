import { useState, useCallback } from 'react';
import { generateCertificatesApi } from '../services/certificateApi';
import { SYSTEM_FIELDS } from '../components/DataMapping';

export function useCertificateGeneration() {
  const [templateFile, setTemplateFile] = useState(null);
  const [uploadedData, setUploadedData] = useState(null);
  const [mapping, setMapping] = useState({});
  const [validation, setValidation] = useState({ isValid: false, blockingErrors: [] });

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

      setGenerationProgress(`Generating ${mappedParticipants.length} certificate(s) via backend engine...`);

      const response = await generateCertificatesApi({
        templateFile,
        participants: mappedParticipants,
        format: 'png',
      });

      if (!response || !response.certificates || response.certificates.length === 0) {
        throw new Error('Backend did not return any generated certificates.');
      }

      setGeneratedCertificates(response.certificates);
      setSelectedCertificate(response.certificates[0]);
      setIsGenerating(false);
      setGenerationProgress('');
    } catch (err) {
      setIsGenerating(false);
      setGenerationProgress('');
      setGenerationError(err.message || 'Certificate generation failed. Please check your uploaded data and try again.');
    }
  }, [templateFile, uploadedData, mapping, validation]);

  return {
    templateFile,
    setTemplateFile,
    uploadedData,
    handleDataLoaded,
    handleClearData,
    handleClearTemplate,
    mapping,
    setMapping,
    validation,
    setValidation,
    isGenerating,
    generationProgress,
    generationError,
    generatedCertificates,
    selectedCertificate,
    setSelectedCertificate,
    handleGenerate,
  };
}
