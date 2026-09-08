import React, { useRef, useState } from 'react';
import { FileSpreadsheet, CheckCircle, RefreshCw, UploadCloud, AlertTriangle } from 'lucide-react';
import Papa from 'papaparse';

export default function UploadData({ dataFile, recordCount, onDataLoaded, onClearData }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  const processFile = (file) => {
    if (!file) return;
    setErrorMsg('');
    const fileName = file.name.toLowerCase();

    if (fileName.endsWith('.json')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const parsed = JSON.parse(e.target.result);
          if (!Array.isArray(parsed) || parsed.length === 0) {
            setErrorMsg('JSON file must contain a non-empty array of participant records.');
            return;
          }
          // Extract unique keys
          const allKeys = new Set();
          parsed.forEach((row) => {
            if (typeof row === 'object' && row !== null) {
              Object.keys(row).forEach((k) => allKeys.add(k));
            }
          });
          onDataLoaded({
            file,
            fileName: file.name,
            records: parsed,
            columns: Array.from(allKeys),
          });
        } catch (err) {
          setErrorMsg(`Invalid JSON file: ${err.message}`);
        }
      };
      reader.readAsText(file);
    } else if (fileName.endsWith('.csv')) {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (results.errors && results.errors.length > 0 && results.data.length === 0) {
            setErrorMsg(`Error parsing CSV: ${results.errors[0].message}`);
            return;
          }
          if (results.data.length === 0) {
            setErrorMsg('CSV file is empty.');
            return;
          }
          onDataLoaded({
            file,
            fileName: file.name,
            records: results.data,
            columns: results.meta.fields || Object.keys(results.data[0] || {}),
          });
        },
        error: (err) => {
          setErrorMsg(`Failed to read CSV: ${err.message}`);
        },
      });
    } else {
      setErrorMsg('Supported data file formats: CSV, JSON.');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
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
    setErrorMsg('');
    onClearData();
    if (fileInputRef.current) fileInputRef.current.value = '';
    fileInputRef.current?.click();
  };

  return (
    <div
      className={`upload-box ${isDragOver ? 'drag-over' : ''} ${dataFile ? 'has-file' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClickBox}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv, .json, text/csv, application/json"
        style={{ display: 'none' }}
        onChange={(e) => processFile(e.target.files[0])}
      />

      <div className="upload-icon">
        {dataFile ? <CheckCircle size={26} color="#10b981" /> : <FileSpreadsheet size={26} />}
      </div>

      <h4 className="upload-title">Upload Data</h4>
      <p className="upload-hint">Upload participant data (Supported: CSV, JSON)</p>

      {errorMsg && (
        <div style={{ color: '#f87171', fontSize: '12px', marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
          <AlertTriangle size={14} />
          <span>{errorMsg}</span>
        </div>
      )}

      {dataFile ? (
        <div>
          <div className="file-details-badge">
            <CheckCircle size={15} />
            <span>✓ {dataFile.name} — {recordCount} records detected</span>
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
          <span>Upload Data</span>
        </button>
      )}
    </div>
  );
}
