import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Brand } from "../components/Layout.jsx";
import { Button, Message } from "../components/ui.jsx";

export default function Login() {
  const { login, notice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "", remember: true });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.email.trim() || !form.password) {
      setError("Введите e-mail и пароль");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(form.email.trim(), form.password, form.remember);
      navigate(location.state?.from || "/profile", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <Brand />
        <h1>Вход в систему</h1>
        <p>Доступ к генерации рецептов, истории и отчётам.</p>
        {notice && !error && <div style={{ marginBottom: 14 }}><Message kind="warn">{notice}</Message></div>}
        {error && <div style={{ marginBottom: 14 }}><Message kind="error">{error}</Message></div>}
        <form className="form" onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="email">Электронная почта</label>
            <input id="email" type="email" autoComplete="username" placeholder="e-mail пользователя"
                   value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="password">Пароль</label>
            <input id="password" type="password" autoComplete="current-password" placeholder="пароль"
                   value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={form.remember} onChange={(e) => setForm({ ...form, remember: e.target.checked })} />
            <span>Запомнить устройство</span>
          </label>
          <Button type="submit" className="primary" busy={busy}>Войти</Button>
          <Link className="btn" to="/register">Создать учётную запись</Link>
        </form>
      </section>
      <section className="auth-side">
        <div className="auth-preview">
          <div className="preview-header">
            <strong>Что умеет система</strong>
            <span className="status ok">АС ГРСН</span>
          </div>
          <div className="preview-grid">
            <div className="preview-tile">
              <strong>Цель</strong>
              <div className="pill-row">
                <span className="tag amber">Снижение веса</span>
                <span className="tag green">Набор массы</span>
                <span className="tag blue">Поддержание</span>
                <span className="tag teal">Выносливость</span>
              </div>
            </div>
            <div className="preview-tile">
              <strong>Калорийность</strong>
              <div className="metric">
                <span>Цель на день</span>
                <strong style={{ fontSize: 16 }}>BMR × k + Δ</strong>
              </div>
            </div>
            <div className="preview-tile">
              <strong>Запреты</strong>
              <div className="pill-row">
                <span className="tag red">Аллерген</span>
                <span className="tag red">Продукт</span>
                <span className="tag amber">Вещество</span>
              </div>
              <p className="muted small" style={{ margin: "12px 0 0" }}>Каждый рецепт проверяется на запреты, включая составные продукты.</p>
            </div>
            <div className="preview-tile">
              <strong>Рецепт</strong>
              <span className="muted">Генерация моделью GigaChat с проверкой БЖУ, калорийности и пошаговой инструкцией.</span>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
