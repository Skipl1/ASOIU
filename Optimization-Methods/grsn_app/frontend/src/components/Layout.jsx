import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const NAV = [
  ["/profile", "Профиль"],
  ["/restrictions", "Запреты"],
  ["/ingredients", "Ингредиенты"],
  ["/generate", "Генерация"],
  ["/history", "История"],
  ["/reports", "Отчёты"],
  ["/analysis", "Анализ"],
];

export function Brand({ caption = "Спортивное питание" }) {
  return (
    <div className="brand">
      <div className="brand-mark">АС</div>
      <div>
        <strong>АС ГРСН</strong>
        <span>{caption}</span>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, isAdmin, logout } = useAuth();
  const items = isAdmin ? [...NAV, ["/admin", "Администрирование"]] : NAV;
  return (
    <div className="app">
      <aside className="sidebar">
        <Brand />
        <nav className="nav" aria-label="Разделы">
          {items.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : undefined)}>
              {label}
            </NavLink>
          ))}
          <button type="button" className="btn small mobile-only" onClick={logout}>Выйти</button>
        </nav>
        <div className="sidebar-footer">
          Пользователь: {user?.name}
          <br />
          {user?.email}
          <br />
          Роль: {isAdmin ? "администратор" : "пользователь"}
          <button type="button" className="btn small" onClick={logout}>Выйти</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
