import React, { useRef, useState, useEffect } from 'react';
import { Image as ImageIcon, FileText, CheckCircle, RefreshCw, UploadCloud } from 'lucide-react';

export default function UploadTemplate({ templateFile, onTemplateSelected, onClearTemplate }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isPdf, setIsPdf] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!templateFile) {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setIsPdf(false);
      return;
    }

    const name = templateFile.name.toLowerCase();
    const pdf = name.endsWith('.pdf') || templateFile.type === 'application/pdf';
    setIsPdf(pdf);

    if (!pdf) {
      const url = URL.createObjectURL(templateFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [templateFile]);

  const handleFile = (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    const isImage = name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || file.type.startsWith('image/');
    const isPdfFile = name.endsWith('.pdf') || file.type === 'application/pdf';

    if (!isImage && !isPdfFile) {
      alert('Please upload a valid certificate template: Image (PNG, JPG) or PDF.');
      return;
    }

    onTemplateSelected(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleClickBox = () => {
    fileInputRef.current?.click();
  };

  const handleReplace = (e) => {
    e.stopPropagation();
    onClearTemplate();
    if (fileInputRef.current) fileInputRef.current.value = '';
    fileInputRef.current?.click();
  };

  return (
    <div
      className={`upload-box ${isDragOver ? 'drag-over' : ''} ${templateFile ? 'has-file' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClickBox}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/jpg,application/pdf"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />

      <div className="upload-icon">
        {templateFile ? (
          isPdf ? <FileText size={28} color="#10b981" /> : <CheckCircle size={28} color="#10b981" />
        ) : (
          <ImageIcon size={28} />
        )}
      </div>

      <h4 className="upload-title">1. Upload Certificate Template</h4>
      <p className="upload-hint">Upload your certificate background template (PNG, JPG, or PDF)</p>

      {templateFile ? (
        <div style={{ marginTop: '8px', textAlign: 'center' }}>
          {previewUrl && (
            <div style={{ marginBottom: '10px' }}>
              <img
                src={previewUrl}
                alt="Template Preview"
                style={{
                  maxHeight: '90px',
                  maxWidth: '180px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.15)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  objectFit: 'contain'
                }}
              />
            </div>
          )}
          <div className="file-details-badge">
            {isPdf ? <FileText size={15} /> : <CheckCircle size={15} />}
            <span>✓ {templateFile.name} ({(templateFile.size / 1024).toFixed(1)} KB)</span>
          </div>
          <div style={{ marginTop: '10px' }}>
            <button type="button" className="btn-secondary btn-sm" onClick={handleReplace}>
              <RefreshCw size={13} />
              <span>Replace Template</span>
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); handleClickBox(); }}>
          <UploadCloud size={14} />
          <span>Browse File (PNG, JPG, PDF)</span>
        </button>
      )}
    </div>
  );
}
