import React from 'react';
import { Award, FileSpreadsheet } from 'lucide-react';

export default function EmptyState() {
  return (
    <div className="empty-state-card">
      <div className="empty-icon-circle">
        <Award size={32} />
      </div>
      <h3 className="empty-title">No certificates generated yet.</h3>
      <p className="empty-description">
        Upload your template and participant data to generate certificates.
      </p>
    </div>
  );
}
