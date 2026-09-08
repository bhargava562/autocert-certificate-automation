/**
 * Certificate Automation API Client
 * Interacts with the FastAPI backend without fake/demo data.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

export async function generateCertificatesApi({ templateFile, participants, format = 'png' }) {
  const formData = new FormData();
  formData.append('template', templateFile);
  formData.append('participants', JSON.stringify(participants));
  formData.append('format', format);

  const res = await fetch(`${API_BASE_URL}/api/certificates/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = 'Certificate generation failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = `Server returned status ${res.status}`;
    }
    throw new Error(errorDetail);
  }

  return await res.json();
}

export function getCertificateImageUrl(filename) {
  if (!filename) return '';
  return `${API_BASE_URL}/api/certificates/download/${encodeURIComponent(filename)}`;
}
