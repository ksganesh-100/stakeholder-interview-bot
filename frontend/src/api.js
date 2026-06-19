// Thin fetch wrappers around the backend API.

async function request(path, { method = "GET", body, passcode } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (passcode) headers["X-Admin-Passcode"] = passcode;

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json();
}

// ── Public (stakeholder) ──
export const getProject = (publicId) => request(`/projects/${publicId}`);

export const startInterview = (publicId, name, role) =>
  request(`/projects/${publicId}/interviews`, {
    method: "POST",
    body: { name, role },
  });

export const sendMessage = (interviewId, message) =>
  request(`/interviews/${interviewId}/messages`, {
    method: "POST",
    body: { message },
  });

// ── Admin ──
export const createProject = (passcode, name, client_name) =>
  request(`/admin/projects`, { method: "POST", body: { name, client_name }, passcode });

export const listProjects = (passcode) =>
  request(`/admin/projects`, { passcode });

export const getProjectInterviews = (passcode, publicId) =>
  request(`/admin/projects/${publicId}/interviews`, { passcode });

export const runSynthesis = (passcode, publicId) =>
  request(`/admin/projects/${publicId}/synthesis`, { method: "POST", passcode });
