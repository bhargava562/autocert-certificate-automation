import React, { useRef, useState } from 'react';
import { FileSpreadsheet, CheckCircle, RefreshCw, UploadCloud, AlertTriangle } from 'lucide-react';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';

export default function UploadData({ dataFile, recordCount, onDataLoaded, onClearData }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  const processFile = (file) => {
    if (!file) return;
    setErrorMsg('');
    const fileName = file.name.toLowerCase();

    if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          if (!firstSheetName) {
            setErrorMsg('Excel file contains no readable sheets.');
            return;
          }
          const worksheet = workbook.Sheets[firstSheetName];
          if (!worksheet || !worksheet['!ref']) {
            setErrorMsg('Excel sheet contains no data.');
            return;
          }

          const range = XLSX.utils.decode_range(worksheet['!ref']);
          const headers = [];
          for (let C = range.s.c; C <= range.e.c; ++C) {
            const cell = worksheet[XLSX.utils.encode_cell({ r: range.s.r, c: C })];
            const headerText = cell && cell.v !== undefined ? String(cell.v).trim() : `Column_${C + 1}`;
            headers.push(headerText);
          }

          const cleanRows = [];
          for (let R = range.s.r + 1; R <= range.e.r; ++R) {
            const row = {};
            let hasData = false;
            for (let C = range.s.c; C <= range.e.c; ++C) {
              const header = headers[C - range.s.c];
              const cell = worksheet[XLSX.utils.encode_cell({ r: R, c: C })];
              if (!cell || cell.v === undefined || cell.v === null || cell.v === '') {
                row[header] = '';
                continue;
              }
              hasData = true;
              let val = cell.v;
              // If formatted text exists and is NOT scientific notation, use formatted text (keeps date formatting)
              if (cell.w && !/^[0-9.]+[eE][+-][0-9]+$/.test(cell.w)) {
                val = String(cell.w).trim();
              } else if (typeof val === 'number') {
                // Prevent scientific notation for large integer IDs and numbers
                if (Number.isInteger(val)) {
                  val = String(BigInt(Math.round(val)));
                } else {
                  val = String(val);
                }
              } else {
                val = String(val).trim();
              }
              row[header] = val;
            }
            if (hasData) cleanRows.push(row);
          }

          if (cleanRows.length === 0) {
            setErrorMsg('Excel sheet contains no data rows.');
            return;
          }

          onDataLoaded({
            file,
            fileName: file.name,
            records: cleanRows,
            columns: headers.filter(Boolean),
          });
        } catch (err) {
          setErrorMsg(`Failed to parse Excel file: ${err.message}`);
        }
      };
      reader.readAsArrayBuffer(file);
    } else if (fileName.endsWith('.json')) {
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
          const cleanRows = parsed.map((row) => {
            const clean = {};
            if (typeof row === 'object' && row !== null) {
              Object.entries(row).forEach(([k, v]) => {
                const cleanK = k.trim();
                clean[cleanK] = typeof v === 'string' ? v.trim() : v;
                allKeys.add(cleanK);
              });
            }
            return clean;
          });
          onDataLoaded({
            file,
            fileName: file.name,
            records: cleanRows,
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
          const rawFields = results.meta.fields || Object.keys(results.data[0] || {});
          const trimmedColumns = rawFields.map((f) => f.trim()).filter(Boolean);
          const cleanRows = results.data.map((row) => {
            const clean = {};
            Object.entries(row).forEach(([k, v]) => {
              const cleanK = k.trim();
              clean[cleanK] = typeof v === 'string' ? v.trim() : v;
            });
            return clean;
          });
          onDataLoaded({
            file,
            fileName: file.name,
            records: cleanRows,
            columns: trimmedColumns,
          });
        },
        error: (err) => {
          setErrorMsg(`Failed to read CSV: ${err.message}`);
        },
      });
    } else {
      setErrorMsg('Supported data formats: CSV, JSON, Excel (XLSX/XLS).');
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
        accept=".csv, .json, .xlsx, .xls, text/csv, application/json, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
        style={{ display: 'none' }}
        onChange={(e) => processFile(e.target.files[0])}
      />

      <div className="upload-icon">
        {dataFile ? <CheckCircle size={26} color="#10b981" /> : <FileSpreadsheet size={26} />}
      </div>

      <h4 className="upload-title">Upload Data</h4>
      <p className="upload-hint">Upload participant data (Supported: CSV, JSON, Excel XLSX/XLS)</p>

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
