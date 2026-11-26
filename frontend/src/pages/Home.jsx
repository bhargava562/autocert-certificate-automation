import React, { useState, useEffect } from 'react';
import { PlusCircle, ChevronUp, ChevronDown, Award, FileSpreadsheet, Layers, Send, AlertTriangle, Loader2 } from 'lucide-react';
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
  const [batchEmailNotice, setBatchEmailNotice] = useState(null);

  const {
    templateFile,
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
    generatedCertificates,
    selectedCertificate,
    setSelectedCertificate,
    handleGenerate,
    handleSendBatchEmails,
    handleResendEmail,
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

  // When generation completes, keep workflow accessible or scroll down
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

      {/* 2. Operations Dashboard Overview Metrics */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
            <Award size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', fontWeight: 600 }}>Certificates Generated</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {generatedCertificates.length > 0 ? generatedCertificates.length : '0 Ready'}
            </div>
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'rgba(59, 130, 246, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3b82f6' }}>
            <Send size={20} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', fontWeight: 600 }}>Emails Dispatched</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
              {emailStats.sent > 0 ? `${emailStats.sent} Sent` : '0 Dispatched'}
            </div>
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'rgba(245, 158, 11, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f59e0b' }}>
            <Layers size={20} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', fontWeight: 600 }}>Template Engine</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              PNG, JPG & Vector PDF
            </div>
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'rgba(139, 92, 246, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b5cf6' }}>
            <FileSpreadsheet size={20} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', fontWeight: 600 }}>Data Ingestion</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              CSV, JSON & Excel XLSX
            </div>
          </div>
        </div>
      </section>

      {/* Hero Action Bar */}
      <section className="hero-action-bar">
        <div className="hero-text">
          <h2>Generate Certificates</h2>
          <p>
            Batch process certificates from custom templates and your participant roster with optional bulk email dispatch.
          </p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={() => setIsWorkflowOpen((prev) => !prev)}
        >
          <PlusCircle size={18} />
          <span>{isWorkflowOpen ? 'Hide Generation Workflow' : 'Generate Certificate'}</span>
          {isWorkflowOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </section>

      {/* 3. Generation Interface (Workflow Section) */}
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
              onTemplateSelected={handleTemplateSelected}
              onClearTemplate={handleClearTemplate}
              extractedPlaceholders={extractedPlaceholders}
              isInspectingTemplate={isInspectingTemplate}
              templateInspectError={templateInspectError}
            />

            <UploadData
              dataFile={uploadedData?.file}
              recordCount={uploadedData?.records?.length || 0}
              onDataLoaded={handleDataLoaded}
              onClearData={handleClearData}
            />
          </div>

          {/* Data Mapping Interface */}
          {uploadedData && (
            <DataMapping
              columns={uploadedData.columns}
              mapping={mapping}
              onMappingChange={setMapping}
              placeholders={extractedPlaceholders}
              isInspectingTemplate={isInspectingTemplate}
              sendEmails={sendEmails}
              onSendEmailsChange={setSendEmails}
              emailSubject={emailSubject}
              onEmailSubjectChange={setEmailSubject}
              outputFormat={outputFormat}
              onOutputFormatChange={setOutputFormat}
            />
          )}

          {/* Validation Summary */}
          {uploadedData && (
            <ValidationSummary
              records={uploadedData.records}
              mapping={mapping}
              placeholders={extractedPlaceholders}
              sendEmails={sendEmails}
              onValidationChange={setValidation}
            />
          )}

          {/* Generation Button */}
          <GenerateButton
            isReady={isReadyToGenerate}
            isGenerating={isGenerating}
            totalRecords={uploadedData?.records?.length || 0}
            onClick={handleGenerate}
          />
        </section>
      )}

      {/* 4. Generation Progress / Status */}
      <GenerationProgress
        isGenerating={isGenerating}
        totalCount={uploadedData?.records?.length || 0}
        progressText={generationProgress}
        error={generationError}
      />

      {/* 5. Generated Certificates Section */}
      <section style={{ marginTop: '36px' }}>
        <div className="generated-section-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <h2 className="section-title">Generated Certificates</h2>
          {generatedCertificates.length > 0 && (() => {
            const overflowCount = generatedCertificates.filter((c) => c.overflowed).length;
            const pendingEmailCount = generatedCertificates.filter(
              (c) => c.status === 'Generated' && c.email && c.filename && c.email_status !== 'Sent'
            ).length;

            const onDispatchBatchEmails = async () => {
              setBatchEmailNotice(null);
              try {
                const res = await handleSendBatchEmails();
                setBatchEmailNotice({
                  type: 'success',
                  text: `Batch email dispatch finished: ${res?.sent_count ?? 0} sent, ${res?.failed_count ?? 0} failed.`,
                });
              } catch (err) {
                setBatchEmailNotice({
                  type: 'error',
                  text: err.message || 'Batch email dispatch failed.',
                });
              }
            };

            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Total: {generatedCertificates.length} certificate(s) generated
                  {emailStats.sent > 0 && ` • ${emailStats.sent} email(s) dispatched`}
                </span>
                {overflowCount > 0 && (
                  <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                    <AlertTriangle size={13} />
                    {overflowCount} overflow warning(s)
                  </span>
                )}
                {pendingEmailCount > 0 && (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={isSendingBatchEmails}
                    onClick={onDispatchBatchEmails}
                  >
                    {isSendingBatchEmails ? <Loader2 size={14} className="spin" /> : <Send size={14} />}
                    <span>
                      {isSendingBatchEmails
                        ? 'Sending Batch Emails...'
                        : `Send Batch Emails (${pendingEmailCount})`}
                    </span>
                  </button>
                )}
              </div>
            );
          })()}
        </div>

        {batchEmailNotice && (
          <div
            role="status"
            style={{
              marginBottom: '14px',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              background:
                batchEmailNotice.type === 'error'
                  ? 'rgba(239, 68, 68, 0.1)'
                  : 'rgba(16, 185, 129, 0.1)',
              border:
                batchEmailNotice.type === 'error'
                  ? '1px solid rgba(239, 68, 68, 0.3)'
                  : '1px solid rgba(16, 185, 129, 0.3)',
              color: batchEmailNotice.type === 'error' ? '#f87171' : '#34d399',
            }}
          >
            {batchEmailNotice.text}
          </div>
        )}

        {/* Initially empty: Show EmptyState */}
        {generatedCertificates.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="split-view-container">
            <CertificateList
              certificates={generatedCertificates}
              selectedId={selectedCertificate?.certificate_id}
              onSelectCertificate={setSelectedCertificate}
              onResendEmail={handleResendEmail}
            />

            <CertificatePreview
              certificate={selectedCertificate}
              onResendEmail={handleResendEmail}
            />
          </div>
        )}
      </section>
    </div>
  );
}
