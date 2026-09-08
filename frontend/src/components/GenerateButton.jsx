import React from 'react';
import { PlayCircle, Loader2 } from 'lucide-react';

export default function GenerateButton({
  isReady,
  isGenerating,
  onClick,
  totalRecords = 0,
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginTop: '16px' }}>
      <button
        type="button"
        className="btn-primary"
        disabled={!isReady || isGenerating}
        onClick={onClick}
      >
        {isGenerating ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            <span>Generating Certificates...</span>
          </>
        ) : (
          <>
            <PlayCircle size={18} />
            <span>Generate Certificates {totalRecords > 0 ? `(${totalRecords})` : ''}</span>
          </>
        )}
      </button>
    </div>
  );
}
