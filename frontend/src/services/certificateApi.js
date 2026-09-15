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

export async function inspectTemplateApi(templateFile) {
  if (!templateFile) return { has_placeholders: false, placeholders: [] };
  const formData = new FormData();
  formData.append('template', templateFile);

  try {
    const res = await fetch(`${API_BASE_URL}/api/certificates/inspect-template`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) return { has_placeholders: false, placeholders: [] };
    return await res.json();
  } catch {
    return { has_placeholders: false, placeholders: [] };
  }
}

export async function generateCertificatesApi({
  templateFile,
  participants,
  format = 'png',
  sendEmails = false,
  emailSubject = '',
}) {
  const formData = new FormData();
  formData.append('template', templateFile);
  formData.append('participants', JSON.stringify(participants));
  formData.append('format', format);
  formData.append('send_emails', String(sendEmails));
  if (emailSubject) {
    formData.append('email_subject', emailSubject);
  }

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

export async function sendSingleEmailApi(payload) {
  const res = await fetch(`${API_BASE_URL}/api/certificates/send-single-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorDetail = 'Sending email failed';
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

export async function testSmtpApi() {
  const res = await fetch(`${API_BASE_URL}/api/certificates/test-smtp`, {
    method: 'POST',
  });

  if (!res.ok) {
    let errorDetail = 'SMTP test failed';
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
