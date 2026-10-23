// Клиент REST API АС ГРСН (/api/v1, JSON, JWT в заголовке Authorization)

const BASE = "/api/v1";

let token = null;
let unauthorizedHandler = () => {};

export function setToken(value) {
  token = value;
}

export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function buildUrl(path, params) {
  const url = new URL(path.startsWith("/api/") ? path : BASE + path, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return url;
}

export async function api(path, { method = "GET", body, params, raw = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Сервер недоступен. Проверьте подключение к сети", 0, null);
  }

  if (response.status === 401 && token) unauthorizedHandler();
  if (response.ok && raw) return response;
  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : `Ошибка ${response.status}`;
    throw new ApiError(detail, response.status, data);
  }
  return data;
}

export async function downloadFile(path, fallbackName) {
  const response = await api(path, { raw: true });
  const disposition = response.headers.get("content-disposition") || "";
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
  const name = match ? decodeURIComponent(match[1] || match[2]) : fallbackName;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
