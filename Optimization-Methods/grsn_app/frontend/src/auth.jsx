// Сессия пользователя: JWT с ограниченным сроком (30 мин), продление при активности,
// автоматическое завершение при бездействии (ТЗ 4.3).
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, onUnauthorized, setToken } from "./api.js";

const STORAGE_KEY = "grsn.session";
const AuthContext = createContext(null);

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    return session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

function store(session, remember) {
  try {
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    if (session) (remember ? localStorage : sessionStorage).setItem(STORAGE_KEY, JSON.stringify({ ...session, remember }));
  } catch {
    /* хранилище недоступно — сессия живёт только в памяти */
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    const stored = readStored();
    if (stored) setToken(stored.token);
    return stored;
  });
  const [notice, setNotice] = useState(null);
  const lastActivity = useRef(Date.now());

  const apply = useCallback((auth, remember) => {
    const next = { token: auth.accessToken, user: auth.user, expiresAt: Date.now() + auth.expiresIn * 1000 };
    setToken(next.token);
    store(next, remember);
    setSession(next);
    return next;
  }, []);

  const clear = useCallback((message) => {
    setToken(null);
    store(null);
    setSession(null);
    if (message) setNotice(message);
  }, []);

  const login = useCallback(async (email, password, remember) => {
    const auth = await api("/auth/login", { method: "POST", body: { email, password } });
    setNotice(null);
    return apply(auth, remember);
  }, [apply]);

  const register = useCallback(async (name, email, password) => {
    const auth = await api("/auth/register", { method: "POST", body: { name, email, password } });
    setNotice(null);
    return apply(auth, false);
  }, [apply]);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* токен мог уже истечь */
    }
    clear();
  }, [clear]);

  useEffect(() => {
    onUnauthorized(() => clear("Сессия завершена. Войдите снова"));
  }, [clear]);

  // Учёт активности пользователя
  useEffect(() => {
    const mark = () => { lastActivity.current = Date.now(); };
    const events = ["mousedown", "keydown", "touchstart", "scroll"];
    events.forEach((e) => window.addEventListener(e, mark, { passive: true }));
    return () => events.forEach((e) => window.removeEventListener(e, mark));
  }, []);

  // Продление токена при активности и выход при бездействии
  useEffect(() => {
    if (!session) return undefined;
    const timer = setInterval(async () => {
      const left = session.expiresAt - Date.now();
      if (left <= 0) {
        clear("Сессия завершена из-за бездействия");
        return;
      }
      const active = Date.now() - lastActivity.current < 5 * 60 * 1000;
      if (left < 10 * 60 * 1000 && active) {
        try {
          const auth = await api("/auth/refresh", { method: "POST" });
          apply(auth, session.remember);
        } catch {
          /* обработка 401 выполнит выход */
        }
      }
    }, 30 * 1000);
    return () => clearInterval(timer);
  }, [session, apply, clear]);

  const value = useMemo(() => ({
    session,
    user: session?.user || null,
    isAdmin: session?.user?.role === "admin",
    notice,
    login,
    register,
    logout,
  }), [session, notice, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
