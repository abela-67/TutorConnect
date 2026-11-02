// Thin fetch wrapper: JWT auth, one-time silent token refresh, DRF error parsing, file download.
const BASE: string = (import.meta.env.VITE_API_URL as string | undefined) || "/api";
const ACCESS = "tc_access";
const REFRESH = "tc_refresh";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode): the session simply will not persist */
  }
}

export const tokens = {
  get access() {
    return read(ACCESS);
  },
  get refresh() {
    return read(REFRESH);
  },
  save(access: string, refresh?: string) {
    write(ACCESS, access);
    if (refresh) write(REFRESH, refresh);
  },
  clear() {
    write(ACCESS, null);
    write(REFRESH, null);
  },
};

function messageFrom(data: any, status: number): string {
  if (data && typeof data === "object") {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data)) return data.map(String).join(" ");
    if (Array.isArray(data.non_field_errors)) return data.non_field_errors.join(" ");
    if (Object.keys(data).length) return "Please check the highlighted fields.";
  }
  if (status === 0) return "Cannot reach the server. Check your connection and try again.";
  if (status >= 500) return "Something went wrong on our side. Please try again later.";
  if (status === 403) return "You do not have permission to do that.";
  if (status === 404) return "We could not find what you were looking for.";
  return `The request could not be completed (${status}).`;
}

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(status: number, data: any) {
    super(messageFrom(data, status));
    this.status = status;
    this.data = data;
  }
}

export function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong.";
}

/** DRF validation errors -> { field: "first message" } so forms can show them beside inputs. */
export function fieldErrors(e: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (e instanceof ApiError && e.data && typeof e.data === "object" && !Array.isArray(e.data)) {
    for (const [k, v] of Object.entries(e.data as Record<string, unknown>)) {
      if (k === "detail" || k === "non_field_errors" || k === "missing") continue;
      out[k] = Array.isArray(v) ? String(v[0]) : typeof v === "string" ? v : "Invalid value.";
    }
  }
  return out;
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

let refreshing: Promise<boolean> | null = null;
function refreshAccess(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = tokens.refresh;
      if (!refresh) return false;
      try {
        const res = await fetch(`${BASE}/auth/token/refresh/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        tokens.save(data.access, data.refresh);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

async function send(method: Method, path: string, body?: unknown, retry = true): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const access = tokens.access;
  if (access) headers.Authorization = `Bearer ${access}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(BASE + path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, null);
  }
  if (res.status === 401 && retry && tokens.refresh && !path.startsWith("/auth/token")) {
    if (await refreshAccess()) return send(method, path, body, false);
    tokens.clear();
    window.dispatchEvent(new Event("tc:logout"));
  }
  return res;
}

async function call<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const res = await send(method, path, body);
  if (res.status === 204) return undefined as T;
  let data: any = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const api = {
  get: <T>(path: string) => call<T>("GET", path),
  post: <T>(path: string, body?: unknown) => call<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => call<T>("PATCH", path, body ?? {}),
  del: <T = void>(path: string) => call<T>("DELETE", path),
  /** Authenticated file download (private credentials are never available through a public URL). */
  async download(path: string, fallbackName = "download") {
    const res = await send("GET", path);
    if (!res.ok) {
      let data: any = null;
      try {
        data = await res.json();
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, data);
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
    const name = m ? decodeURIComponent(m[1]) : fallbackName;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
