const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function handleUnauthorized() {
  localStorage.removeItem("token");
  if (window.location.pathname !== "/login") {
    window.location.href = `/login?message=${encodeURIComponent("Session expired. Please log in again.")}`;
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    let errorDetail = "An error occurred";
    try {
      const data = await res.json();
      errorDetail = data.detail || errorDetail;
    } catch {
      errorDetail = `Request failed with status ${res.status}`;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

// ---------------- AUTH ----------------
export async function registerUser(email, password, role, fullName) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, role, full_name: fullName }),
  });
  return handleResponse(res);
}

export async function loginUser(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function getMe() {
  const res = await fetch(`${BASE_URL}/auth/me`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- MEDICATIONS ----------------
export async function getMedications(patientId) {
  const res = await fetch(`${BASE_URL}/medications/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function addMedication(payload) {
  const res = await fetch(`${BASE_URL}/medications`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

// ---------------- INTERACTIONS ----------------
export async function getInteractions(patientId) {
  const res = await fetch(`${BASE_URL}/interactions/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- EFFECTIVENESS ----------------
export async function logEffectiveness(payload) {
  const res = await fetch(`${BASE_URL}/effectiveness`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getPatientEffectiveness(patientId) {
  const res = await fetch(`${BASE_URL}/effectiveness/patient/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- ENCOUNTERS ----------------
export async function startEncounter(patientId, durationMinutes = 60) {
  const res = await fetch(`${BASE_URL}/encounters/start`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ patient_id: patientId, duration_minutes: durationMinutes }),
  });
  return handleResponse(res);
}

export async function closeEncounter(encounterId) {
  const res = await fetch(`${BASE_URL}/encounters/${encounterId}/close`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function getPatientEncounters(patientId) {
  const res = await fetch(`${BASE_URL}/encounters/patient/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- CONSENT ----------------
export async function getMyConsents() {
  const res = await fetch(`${BASE_URL}/consent/my`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function getPatientConsents(patientId) {
  const res = await fetch(`${BASE_URL}/consent/patient/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function grantConsent(doctorId, scope = "all", expiresAt = null) {
  const res = await fetch(`${BASE_URL}/consent/grant`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ doctor_id: doctorId, scope, expires_at: expiresAt }),
  });
  return handleResponse(res);
}

export async function revokeConsent(consentId) {
  const res = await fetch(`${BASE_URL}/consent/${consentId}/revoke`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- LINKS ----------------
export async function getMyLinks() {
  const res = await fetch(`${BASE_URL}/links/my`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function requestLink(patientEmail) {
  const res = await fetch(`${BASE_URL}/links/request`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ patient_email: patientEmail }),
  });
  return handleResponse(res);
}

export async function approveLink(linkId) {
  const res = await fetch(`${BASE_URL}/links/${linkId}/approve`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function rejectLink(linkId) {
  const res = await fetch(`${BASE_URL}/links/${linkId}/reject`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- AUDIT ----------------
export async function getAuditLog(patientId) {
  const res = await fetch(`${BASE_URL}/audit/${patientId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

// ---------------- EXPORT ----------------
export async function exportHistoryJson(patientId) {
  const res = await fetch(`${BASE_URL}/export/${patientId}?format=json`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function downloadExportPdf(patientId, filename = "medication_history.pdf") {
  const token = localStorage.getItem("token");
  const res = await fetch(`${BASE_URL}/export/${patientId}?format=pdf`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    let errorDetail = "Failed to export PDF";
    try {
      const err = await res.json();
      errorDetail = err.detail || errorDetail;
    } catch {}
    throw new Error(errorDetail);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
