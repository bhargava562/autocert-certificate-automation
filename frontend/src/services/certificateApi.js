/**
 * Certificate Automation API Client
 * Interacts with the FastAPI backend without fake/demo data.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

async function parseErrorResponse(res, fallbackMessage) {
  try {
    const errJson = await res.json();
    return errJson.detail || fallbackMessage;
  } catch {
    return `Server returned status ${res.status}`;
  }
}

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
  const formData = new FormData();
  formData.append('template', templateFile);

  const res = await fetch(`${API_BASE_URL}/api/templates/inspect`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, 'Template inspection failed'));
  }

  return await res.json();
}

export async function generateCertificatesApi({
  templateFile,
  participants,
  format = 'png',
  sendEmails = false,
  emailSubject = '',
  fieldMapping = null,
}) {
  const formData = new FormData();
  formData.append('template', templateFile);
  formData.append('participants', JSON.stringify(participants));
  formData.append('format', format);
  formData.append('send_emails', String(sendEmails));
  if (emailSubject) {
    formData.append('email_subject', emailSubject);
  }
  if (fieldMapping && Object.keys(fieldMapping).length > 0) {
    formData.append('field_mapping', JSON.stringify(fieldMapping));
  }

  const res = await fetch(`${API_BASE_URL}/api/certificates/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, 'Certificate generation failed'));
  }

  return await res.json();
}

export async function sendBatchEmailsApi(payload) {
  const res = await fetch(`${API_BASE_URL}/api/certificates/send-batch-emails`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, 'Sending batch emails failed'));
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
    throw new Error(await parseErrorResponse(res, 'Sending email failed'));
  }

  return await res.json();
}

export async function testSmtpApi() {
  const res = await fetch(`${API_BASE_URL}/api/certificates/test-smtp`, {
    method: 'POST',
  });

  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, 'SMTP test failed'));
  }

  return await res.json();
}

export function getCertificateImageUrl(pathOrFilename) {
  if (!pathOrFilename) return '';
  if (/^https?:\/\//i.test(pathOrFilename)) {
    return pathOrFilename;
  }
  if (pathOrFilename.startsWith('/')) {
    return `${API_BASE_URL}${pathOrFilename}`;
  }
  return `${API_BASE_URL}/api/certificates/download/${encodeURIComponent(pathOrFilename)}`;
}
