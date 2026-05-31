import Cookies from "js-cookie";

const TOKEN_KEY = "medrag_token";
const REFRESH_KEY = "medrag_refresh_token";
const USER_KEY = "medrag_user";

export function saveToken(token: string, refreshToken?: string) {
  localStorage.setItem(TOKEN_KEY, token);
  Cookies.set(TOKEN_KEY, token, { expires: 1, sameSite: "Lax" });
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY) ?? Cookies.get(TOKEN_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  Cookies.remove(TOKEN_KEY);
}

export function saveUser(user: object) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getUser<T>(): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}
