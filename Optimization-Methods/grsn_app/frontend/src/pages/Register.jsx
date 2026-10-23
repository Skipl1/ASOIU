import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Brand } from "../components/Layout.jsx";
import { Button, Message } from "../components/ui.jsx";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function validate(form) {
  const errors = [];
  if (!form.name.trim()) errors.push("Укажите имя");
  if (!EMAIL_RE.test(form.email.trim())) errors.push("Некорректный адрес электронной почты");
  if (form.password.length < 8) errors.push("Пароль должен содержать не менее 8 символов");
  if (!/[A-Za-zА-Яа-яЁё]/.test(form.password) || !/\d/.test(form.password)) errors.push("Пароль должен содержать буквы и цифры");
  if (form.password !== form.repeat) errors.push("Пароли не совпадают");
  if (!form.consent) errors.push("Необходимо согласие на обработку данных профиля");
  return errors;
}

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", repeat: "", consent: false });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (found.length) return;
    setBusy(true);
    try {
      await register(form.name.trim(), form.email.trim(), form.password);
      navigate("/profile", { replace: true, state: { welcome: true } });
    } catch (err) {
      setErrors([err.message]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page compact">
      <section className="auth-panel">
        <Brand />
        <h1>Регистрация</h1>
        <p>Создайте учётную запись, чтобы перейти к настройке личного профиля.</p>
        {errors.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <Message kind="error">
              {errors.length === 1 ? errors[0] : <ul style={{ margin: 0 }}>{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
            </Message>
          </div>
        )}
        <form className="form" onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="name">Имя</label>
            <input id="name" autoComplete="name" placeholder="как к вам обращаться" value={form.name} onChange={set("name")} />
          </div>
          <div className="field">
            <label htmlFor="email">Электронная почта</label>
            <input id="email" type="email" autoComplete="email" placeholder="e-mail пользователя" value={form.email} onChange={set("email")} />
          </div>
          <div className="field">
            <label htmlFor="password">Пароль</label>
            <input id="password" type="password" autoComplete="new-password" placeholder="пароль" value={form.password} onChange={set("password")} />
            <span className="field-hint">Не менее 8 символов, буквы и цифры</span>
          </div>
          <div className="field">
            <label htmlFor="password-repeat">Повтор пароля</label>
            <input id="password-repeat" type="password" autoComplete="new-password" placeholder="повтор пароля" value={form.repeat} onChange={set("repeat")} />
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={form.consent} onChange={set("consent")} />
            <span>Согласие на обработку данных профиля</span>
          </label>
          <Button type="submit" className="primary" busy={busy}>Зарегистрироваться</Button>
        </form>
        <div className="message-box" style={{ marginTop: 18 }}>
          <strong>Уже есть учётная запись?</strong>
          <br />
          Войдите в систему, чтобы продолжить работу в личном кабинете.
          <div style={{ marginTop: 12 }}>
            <Link className="btn" to="/login">Войти</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
