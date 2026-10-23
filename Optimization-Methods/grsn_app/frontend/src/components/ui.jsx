import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { fmt } from "../format.js";

// ---------- загрузка данных ----------

export function useLoad(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const requestId = useRef(0);

  const reload = useCallback(async () => {
    const id = ++requestId.current;  // ответ на устаревший запрос (например, при вводе в поиск) не должен перезаписывать новый
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await loaderRef.current();
      if (id === requestId.current) setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      if (id === requestId.current) setState((s) => ({ ...s, loading: false, error }));
      return null;
    }
  }, []);

  useEffect(() => {
    reload();
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  const setData = useCallback((updater) => setState((s) => ({ ...s, data: typeof updater === "function" ? updater(s.data) : updater })), []);
  return { ...state, reload, setData };
}

// ---------- уведомления ----------

const ToastContext = createContext(() => {});

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const notify = useCallback((text, kind = "ok") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);
  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>)}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

// ---------- разметка ----------

export function PageHeader({ title, subtitle, children }) {
  return (
    <header className="topbar">
      <div className="page-title">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="top-actions">{children}</div>}
    </header>
  );
}

export function Panel({ title, hint, actions, children, className = "", style, bodyClass = "panel-body" }) {
  return (
    <section className={`panel ${className}`} style={style}>
      {(title || hint || actions) && (
        <div className="panel-header">
          <h2>{title}</h2>
          {actions || (hint && <span>{hint}</span>)}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function Metric({ label, value, hint }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <span style={{ marginTop: 4 }}>{hint}</span>}
    </div>
  );
}

export function Message({ kind = "info", title, children }) {
  return (
    <div className={`message-box ${kind}`} role={kind === "error" ? "alert" : undefined}>
      {title && <strong>{title}</strong>}
      {title && children ? <div style={{ marginTop: 6 }}>{children}</div> : children}
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <Message kind="error">{error.message || String(error)}</Message>;
}

export function Loading({ text = "Загрузка…" }) {
  return <div className="loading-block"><span className="spinner dark" />{text}</div>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function Button({ busy, children, className = "", ...props }) {
  return (
    <button type="button" className={`btn ${className}`} disabled={busy || props.disabled} {...props}>
      {busy && <span className="spinner" />}
      {children}
    </button>
  );
}

export function StatusTag({ status, children }) {
  return <span className={`status ${status}`}>{children}</span>;
}

export function MacroBars({ protein, fat, carbs, grams }) {
  const rows = [
    ["Белки", "protein", protein, grams?.protein],
    ["Жиры", "fat", fat, grams?.fat],
    ["Углеводы", "carbs", carbs, grams?.carbs],
  ];
  return (
    <div className="macro-bars">
      {rows.map(([label, cls, pct, g]) => (
        <div className="bar-line" key={cls}>
          <div className="bar-label">
            <strong style={{ fontWeight: 600 }}>{label}</strong>
            {g !== undefined && <span>{fmt(g, 1)} г</span>}
          </div>
          <div className="bar"><span className={cls} style={{ width: `${Math.min(100, Math.max(0, pct || 0))}%` }} /></div>
          <strong>{fmt(pct, 0)} %</strong>
        </div>
      ))}
    </div>
  );
}

export function Modal({ title, onClose, children, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="panel modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="panel-header">
          <h2>{title}</h2>
          <button type="button" className="btn small ghost" onClick={onClose} aria-label="Закрыть">✕</button>
        </div>
        <div className="panel-body">{children}</div>
        {footer && <div className="panel-body" style={{ borderTop: "1px solid var(--line)" }}><div className="inline" style={{ justifyContent: "flex-end" }}>{footer}</div></div>}
      </div>
    </div>
  );
}

export function Stars({ score }) {
  if (!score) return <span className="muted">—</span>;
  return <span className="score" title={`${score} из 5`}>{"★".repeat(score)}<span className="muted">{"★".repeat(5 - score)}</span></span>;
}

export const CHART_COLORS = { protein: "#5b8cff", fat: "#f3b84e", carbs: "#4fd18b", line: "#4fd18b", grid: "rgba(148,163,184,0.2)", axis: "#94a3b8" };
