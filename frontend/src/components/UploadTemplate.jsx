import React, { useRef, useState } from 'react';
import { Image as ImageIcon, CheckCircle, RefreshCw, UploadCloud } from 'lucide-react';

export default function UploadTemplate({ templateFile, onTemplateSelected, onClearTemplate }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    if (!file.type.includes('png') && !file.name.toLowerCase().endsWith('.png')) {
      alert('Please upload a PNG certificate template image.');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
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
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
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
        accept="image/png"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />

      <div className="upload-icon">
        {templateFile ? <CheckCircle size={26} color="#10b981" /> : <ImageIcon size={26} />}
      </div>

      <h4 className="upload-title">Upload Template</h4>
      <p className="upload-hint">Upload your certificate template (Accepted format: PNG)</p>

      {templateFile ? (
        <div>
          <div className="file-details-badge">
            <CheckCircle size={15} />
            <span>✓ {templateFile.name}</span>
          </div>
          <div style={{ marginTop: '12px' }}>
            <button type="button" className="btn-secondary btn-sm" onClick={handleReplace}>
              <RefreshCw size={13} />
              <span>Replace</span>
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); handleClickBox(); }}>
          <UploadCloud size={14} />
          <span>Upload Template</span>
        </button>
      )}
    </div>
  );
}
