import React, { useState, useEffect } from 'react';
import { PlusCircle, ChevronUp, ChevronDown } from 'lucide-react';
import Header from '../components/Header';
import EmptyState from '../components/EmptyState';
import UploadTemplate from '../components/UploadTemplate';
import UploadData from '../components/UploadData';
import DataMapping from '../components/DataMapping';
import ValidationSummary from '../components/ValidationSummary';
import GenerateButton from '../components/GenerateButton';
import GenerationProgress from '../components/GenerationProgress';
import CertificateList from '../components/CertificateList';
import CertificatePreview from '../components/CertificatePreview';
import { useCertificateGeneration } from '../hooks/useCertificateGeneration';
import { checkBackendHealth } from '../services/certificateApi';

export default function Home() {
  const [backendConnected, setBackendConnected] = useState(true);
  const [isWorkflowOpen, setIsWorkflowOpen] = useState(false);

  const {
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
  } = useCertificateGeneration();

  // Periodic health check
  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      const res = await checkBackendHealth();
      if (isMounted) setBackendConnected(res.ok);
    };
    check();
    const interval = setInterval(check, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // When generation completes, scroll down to the generated list
  useEffect(() => {
    if (generatedCertificates.length > 0) {
      setIsWorkflowOpen(false);
    }
  }, [generatedCertificates]);

  const isReadyToGenerate = Boolean(
    templateFile &&
    uploadedData &&
    uploadedData.records.length > 0 &&
    validation.isValid
  );

  return (
    <div className="app-layout">
      {/* 1. Header */}
      <Header backendConnected={backendConnected} />

      {/* Hero Action Bar */}
      <section className="hero-action-bar">
        <div className="hero-text">
          <h2>Generate Certificates</h2>
          <p>
            Batch process certificates from custom templates and your participant roster.
          </p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={() => setIsWorkflowOpen((prev) => !prev)}
        >
          <PlusCircle size={18} />
          <span>{isWorkflowOpen ? 'Hide Generation Workflow' : 'Generate New Certificate'}</span>
          {isWorkflowOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </section>

      {/* 2. Generation Interface (Workflow Section) */}
      {isWorkflowOpen && (
        <section className="workflow-panel">
          <div className="workflow-header">
            <h3 className="workflow-title">Configure Certificate Batch</h3>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Step 1: Upload Assets → Step 2: Map & Validate → Step 3: Generate
            </span>
          </div>

          <div className="upload-grid">
            <UploadTemplate
              templateFile={templateFile}
              onTemplateSelected={setTemplateFile}
              onClearTemplate={handleClearTemplate}
            />

            <UploadData
              dataFile={uploadedData?.file}
              recordCount={uploadedData?.records?.length || 0}
              onDataLoaded={handleDataLoaded}
              onClearData={handleClearData}
            />
          </div>

          {/* 3. Data Mapping Interface */}
          {uploadedData && (
            <DataMapping
              columns={uploadedData.columns}
              mapping={mapping}
              onMappingChange={setMapping}
            />
          )}

          {/* 4. Validation Summary */}
          {uploadedData && (
            <ValidationSummary
              records={uploadedData.records}
              mapping={mapping}
              onValidationChange={setValidation}
            />
          )}

          {/* 5. Generation Button */}
          <GenerateButton
            isReady={isReadyToGenerate}
            isGenerating={isGenerating}
            totalRecords={uploadedData?.records?.length || 0}
            onClick={handleGenerate}
          />
        </section>
      )}

      {/* 6. Generation Progress / Status */}
      <GenerationProgress
        isGenerating={isGenerating}
        totalCount={uploadedData?.records?.length || 0}
        progressText={generationProgress}
        error={generationError}
      />

      {/* 7. Generated Certificates Section */}
      <section style={{ marginTop: '36px' }}>
        <div className="generated-section-header">
          <h2 className="section-title">Generated Certificates</h2>
          {generatedCertificates.length > 0 && (
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Total: {generatedCertificates.length} certificate(s) generated
            </span>
          )}
        </div>

        {/* Initially empty: Show EmptyState */}
        {generatedCertificates.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="split-view-container">
            <CertificateList
              certificates={generatedCertificates}
              selectedId={selectedCertificate?.certificate_id}
              onSelectCertificate={setSelectedCertificate}
            />

            <CertificatePreview
              certificate={selectedCertificate}
            />
          </div>
        )}
      </section>
    </div>
  );
}
