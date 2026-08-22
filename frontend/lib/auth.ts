import Cookies from "js-cookie";

const TOKEN_KEY = "medrag_token";
const REFRESH_KEY = "medrag_refresh_token";
const USER_KEY = "medrag_user";

/**
 * "Remember me" decides where credentials live. When it is off, the session is
 * kept in sessionStorage and a session cookie, so closing the tab signs the user
 * out — previously the checkbox was rendered but changed nothing.
 */
function store(remember: boolean): Storage {
  return remember ? localStorage : sessionStorage;
}

/** True when the current session was started with "remember me" ticked. */
export function isPersistent(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(TOKEN_KEY) !== null;
}

export function saveToken(token: string, refreshToken?: string, remember = isPersistent()) {
  // Drop any copy in the other storage so a re-login cannot leave a stale token behind.
  const other = remember ? sessionStorage : localStorage;
  other.removeItem(TOKEN_KEY);
  other.removeItem(REFRESH_KEY);

  store(remember).setItem(TOKEN_KEY, token);
  Cookies.set(TOKEN_KEY, token, remember ? { expires: 1, sameSite: "Lax" } : { sameSite: "Lax" });
  if (refreshToken) {
    store(remember).setItem(REFRESH_KEY, refreshToken);
  }
}

function read(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return read(TOKEN_KEY) ?? Cookies.get(TOKEN_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return read(REFRESH_KEY);
}

export function clearAuth() {
  for (const key of [TOKEN_KEY, REFRESH_KEY, USER_KEY]) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }
  Cookies.remove(TOKEN_KEY);
}

export function saveUser(user: object) {
  // Mirror wherever the token already lives so both clear together.
  const target = localStorage.getItem(TOKEN_KEY) ? localStorage : sessionStorage;
  target.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser<T>(): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = read(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}
