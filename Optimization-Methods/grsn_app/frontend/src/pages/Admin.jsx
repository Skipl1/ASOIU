import { useMemo, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Button, Empty, ErrorBox, Loading, Message, Metric, Modal, PageHeader, Panel, StatusTag, useLoad, useToast } from "../components/ui.jsx";
import { fmt, fmtDateTime } from "../format.js";

const TABS = [
  ["users", "Пользователи"],
  ["ingredients", "Ингредиенты"],
  ["categories", "Категории"],
  ["allergens", "Аллергены"],
  ["logs", "Логи"],
  ["backups", "Резервные копии"],
  ["integrity", "Целостность"],
];

const USER_STATUS = { active: ["ok", "активен"], blocked: ["bad", "заблокирован"], deleted: ["warn", "удалён"] };

const splitList = (text) => text.split(/[,;\n]/).map((s) => s.trim()).filter(Boolean);

export default function Admin() {
  const notify = useToast();
  const [tab, setTab] = useState("users");
  const stats = useLoad(() => api("/admin/stats"));
  const [backupBusy, setBackupBusy] = useState(false);
  const [restoreOpen, setRestoreOpen] = useState(false);

  const createBackup = async () => {
    setBackupBusy(true);
    try {
      const res = await api("/admin/backups", { method: "POST" });
      notify(`${res.message}: ${res.fileName}`);
      setTimeout(() => stats.reload(), 2500);
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setBackupBusy(false);
    }
  };

  const s = stats.data;
  return (
    <>
      <PageHeader title="Модуль администрирования" subtitle="Управление пользователями, каталогом, аллергенами и резервными копиями.">
        <Button onClick={() => setRestoreOpen(true)}>Восстановить</Button>
        <Button className="primary" busy={backupBusy} onClick={createBackup}>Создать копию</Button>
      </PageHeader>

      <div className="tabs" role="tablist">
        {TABS.map(([key, label]) => (
          <button type="button" role="tab" aria-selected={tab === key} key={key} className={`tab ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      <section className="layout grid-4 mt-18">
        <Metric label="Пользователи" value={s ? s.users : "…"} hint={s ? `активных ${s.activeUsers} · заблокировано ${s.blockedUsers}` : null} />
        <Metric label="Ингредиенты" value={s ? s.ingredients : "…"} hint={s ? `категорий ${s.categories} · рецептов ${s.recipes}` : null} />
        <Metric label="Аллергены" value={s ? s.allergens : "…"} />
        <Metric label="Ошибки данных" value={s ? s.dataErrors : "…"} hint={s ? `предупреждений ${s.dataWarnings}` : null} />
      </section>

      <div className="mt-18">
        {tab === "users" && <UsersTab stats={s} onChanged={stats.reload} openLogs={() => setTab("logs")} openIntegrity={() => setTab("integrity")} />}
        {tab === "ingredients" && <IngredientsTab onChanged={stats.reload} />}
        {tab === "categories" && <CategoriesTab onChanged={stats.reload} />}
        {tab === "allergens" && <AllergensTab onChanged={stats.reload} />}
        {tab === "logs" && <LogsTab />}
        {tab === "backups" && <BackupsTab onCreate={createBackup} busy={backupBusy} onRestore={() => setRestoreOpen(true)} />}
        {tab === "integrity" && <IntegrityTab />}
      </div>

      {restoreOpen && <RestoreModal onClose={() => setRestoreOpen(false)} onDone={stats.reload} />}
    </>
  );
}

// ---------------- пользователи ----------------

function UsersTab({ stats, onChanged, openLogs, openIntegrity }) {
  const notify = useToast();
  const { user: me } = useAuth();
  const [search, setSearch] = useState("");
  const users = useLoad(() => api("/admin/users", { params: { search } }), [search]);
  const [activity, setActivity] = useState(null);

  const update = async (u, body, message) => {
    try {
      await api(`/admin/users/${u.id}`, { method: "PATCH", body });
      notify(message);
      users.reload();
      onChanged();
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const remove = async (u) => {
    if (!window.confirm(`Удалить учётную запись ${u.email} вместе со всеми данными?`)) return;
    try {
      await api(`/admin/users/${u.id}`, { method: "DELETE" });
      notify("Учётная запись удалена");
      users.reload();
      onChanged();
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const showActivity = async (u) => {
    try {
      setActivity({ user: u, logs: await api(`/admin/users/${u.id}/activity`) });
    } catch (err) {
      notify(err.message, "error");
    }
  };

  return (
    <>
      <Panel title="Учётные записи пользователей" actions={(
        <div className="toolbar-right">
          <input className="search" placeholder="поиск пользователя" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Поиск пользователя" />
        </div>
      )}>
        {users.loading && !users.data ? <Loading /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Пользователь</th><th>E-mail</th><th>Роль</th><th>Статус</th><th>Последний вход</th><th>Рецептов</th><th>Действия</th></tr></thead>
              <tbody>
                {(users.data || []).map((u) => {
                  const [cls, label] = USER_STATUS[u.status];
                  const self = u.id === me.id;
                  return (
                    <tr key={u.id}>
                      <td>{u.name}{self && <span className="tag blue" style={{ marginLeft: 6 }}>вы</span>}</td>
                      <td>{u.email}</td>
                      <td>{u.role === "admin" ? "Администратор" : "Пользователь"}</td>
                      <td><StatusTag status={cls}>{label}</StatusTag>{u.lockedUntil && new Date(u.lockedUntil) > new Date() && <div className="small muted">вход заблокирован до {fmtDateTime(u.lockedUntil)}</div>}</td>
                      <td>{fmtDateTime(u.lastLoginAt)}</td>
                      <td>{u.recipesCount}</td>
                      <td>
                        <div className="table-actions">
                          <button type="button" className="btn small" onClick={() => showActivity(u)}>Открыть</button>
                          {!self && (u.status === "active"
                            ? <button type="button" className="btn small" onClick={() => update(u, { status: "blocked" }, "Пользователь заблокирован")}>Блокировать</button>
                            : <button type="button" className="btn small" onClick={() => update(u, { status: "active" }, "Пользователь разблокирован")}>Разблокировать</button>)}
                          {!self && (u.role === "user"
                            ? <button type="button" className="btn small" onClick={() => update(u, { role: "admin" }, "Назначена роль администратора")}>Сделать админом</button>
                            : <button type="button" className="btn small" onClick={() => update(u, { role: "user" }, "Роль изменена на «пользователь»")}>Снять админа</button>)}
                          {!self && <button type="button" className="btn small" onClick={() => remove(u)}>Удалить</button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel className="mt-18" title="Контроль системы" hint="Логи и копии">
        <div className="list">
          <div className="row-item">
            <div className="row-main"><strong>Последняя резервная копия</strong><span>pg_dump, отдельный том хранилища</span></div>
            <span className={`tag ${stats?.lastBackup ? "green" : "amber"}`}>{stats?.lastBackup ? fmtDateTime(stats.lastBackup) : "не создавалась"}</span>
          </div>
          <div className="row-item">
            <div className="row-main"><strong>Целостность справочников</strong><span>Категории, аллергены, ингредиенты</span></div>
            <button type="button" className={`tag ${stats?.dataErrors ? "red" : stats?.dataWarnings ? "amber" : "green"}`} style={{ cursor: "pointer" }} onClick={openIntegrity}>
              {stats ? (stats.dataErrors ? `ошибок: ${stats.dataErrors}` : stats.dataWarnings ? `предупреждений: ${stats.dataWarnings}` : "в норме") : "…"}
            </button>
          </div>
          <div className="row-item">
            <div className="row-main"><strong>Неудачные входы</strong><span>За последние 7 дней</span></div>
            <span className={`tag ${stats?.failedLogins7d ? "amber" : "green"}`}>{stats ? stats.failedLogins7d : "…"}</span>
          </div>
          <div className="row-item">
            <div className="row-main"><strong>Действия администратора</strong><span>Журнал операций</span></div>
            <button type="button" className="btn small" onClick={openLogs}>Открыть</button>
          </div>
        </div>
      </Panel>

      {activity && (
        <Modal title={`Активность: ${activity.user.email}`} onClose={() => setActivity(null)}>
          {activity.logs.length === 0 ? <Empty>Событий нет</Empty> : <LogTable logs={activity.logs} compact />}
        </Modal>
      )}
    </>
  );
}

// ---------------- ингредиенты ----------------

const EMPTY_INGREDIENT = { id: null, name: "", code: "", categoryId: "", protein100g: "", fat100g: "", carbs100g: "", calories100g: "",
  synonyms: "", allergenIds: [], componentIds: [], compositionDescription: "" };

function IngredientsTab({ onChanged }) {
  const notify = useToast();
  const data = useLoad(async () => {
    const [ingredients, categories, allergens] = await Promise.all([api("/ingredients"), api("/categories"), api("/allergens")]);
    return { ingredients, categories, allergens };
  });
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(EMPTY_INGREDIENT);
  const [componentSearch, setComponentSearch] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const list = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data.data?.ingredients || []).filter((i) => !q || i.name.toLowerCase().includes(q));
  }, [data.data, search]);

  if (data.loading && !data.data) return <Loading />;
  if (data.error) return <ErrorBox error={data.error} />;
  const { categories, allergens, ingredients } = data.data;
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const toggleIn = (key, id) => setForm({ ...form, [key]: form[key].includes(id) ? form[key].filter((x) => x !== id) : [...form[key], id] });
  const atwater = 4 * Number(form.protein100g || 0) + 9 * Number(form.fat100g || 0) + 4 * Number(form.carbs100g || 0);

  const edit = (i) => {
    setError(null);
    setForm({
      id: i.id, name: i.name, code: i.code || "", categoryId: i.categoryId || "", protein100g: String(i.protein100g), fat100g: String(i.fat100g),
      carbs100g: String(i.carbs100g), calories100g: String(i.calories100g), synonyms: i.synonyms.join(", "),
      allergenIds: i.allergens.map((a) => a.id), componentIds: i.components.map((c) => c.id), compositionDescription: i.compositionDescription || "",
    });
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  };

  const save = async (e) => {
    e.preventDefault();
    const num = (v) => Number(String(v).replace(",", "."));
    const body = {
      name: form.name.trim(), code: form.code.trim() || null, categoryId: form.categoryId || null,
      protein100g: num(form.protein100g), fat100g: num(form.fat100g), carbs100g: num(form.carbs100g), calories100g: num(form.calories100g),
      synonyms: splitList(form.synonyms), allergenIds: form.allergenIds, componentIds: form.componentIds,
      isComposite: form.componentIds.length > 0, compositionDescription: form.compositionDescription.trim() || null,
    };
    if (!body.name) return setError(new Error("Укажите название"));
    if ([body.protein100g, body.fat100g, body.carbs100g, body.calories100g].some((v) => Number.isNaN(v) || v < 0)) {
      return setError(new Error("Пищевая ценность должна быть неотрицательными числами"));
    }
    setBusy(true);
    setError(null);
    try {
      if (form.id) await api(`/admin/ingredients/${form.id}`, { method: "PUT", body });
      else await api("/admin/ingredients", { method: "POST", body });
      notify(form.id ? "Ингредиент обновлён" : "Ингредиент добавлен в каталог");
      setForm(EMPTY_INGREDIENT);
      data.reload();
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (i) => {
    if (!window.confirm(`Удалить «${i.name}» из каталога?`)) return;
    try {
      await api(`/admin/ingredients/${i.id}`, { method: "DELETE" });
      notify("Ингредиент удалён");
      data.reload();
      onChanged();
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const componentOptions = ingredients.filter((i) => i.id !== form.id && (!componentSearch || i.name.toLowerCase().includes(componentSearch.toLowerCase())));

  return (
    <>
      <Panel title="Каталог продуктов" actions={(
        <div className="toolbar-right">
          <input className="search" placeholder="поиск ингредиента" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Поиск ингредиента" />
          <Button className="small" onClick={() => { setForm(EMPTY_INGREDIENT); window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); }}>Добавить</Button>
        </div>
      )}>
        <div className="table-wrap" style={{ maxHeight: 460 }}>
          <table>
            <thead><tr><th>Ингредиент</th><th>Категория</th><th>Б / Ж / У</th><th>Ккал</th><th>Аллергены</th><th>Действия</th></tr></thead>
            <tbody>
              {list.map((i) => (
                <tr key={i.id} className={form.id === i.id ? "selected" : ""}>
                  <td>{i.name}{i.isComposite && <span className="tag purple" style={{ marginLeft: 6 }}>составной</span>}</td>
                  <td>{i.categoryName || "—"}</td>
                  <td className="nowrap">{fmt(i.protein100g, 1)} / {fmt(i.fat100g, 1)} / {fmt(i.carbs100g, 1)}</td>
                  <td>{fmt(i.calories100g)}</td>
                  <td>{i.effectiveAllergens.length ? i.effectiveAllergens.map((a) => a.name).join(", ") : "—"}</td>
                  <td><div className="table-actions">
                    <button type="button" className="btn small" onClick={() => edit(i)}>Изменить</button>
                    <button type="button" className="btn small" onClick={() => remove(i)}>Удалить</button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel className="mt-18" title={form.id ? "Редактирование ингредиента" : "Новый ингредиент"} hint="Каталог продуктов">
        <form className="form" onSubmit={save}>
          <div className="form-grid">
            <div className="field"><label htmlFor="ingredient-name">Название</label><input id="ingredient-name" placeholder="название ингредиента" value={form.name} onChange={set("name")} /></div>
            <div className="field">
              <label htmlFor="category">Категория</label>
              <select id="category" value={form.categoryId} onChange={set("categoryId")}>
                <option value="">Выберите категорию</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field"><label htmlFor="protein">Белки на 100 г</label><input id="protein" inputMode="decimal" placeholder="значение" value={form.protein100g} onChange={set("protein100g")} /></div>
            <div className="field"><label htmlFor="fat">Жиры на 100 г</label><input id="fat" inputMode="decimal" placeholder="значение" value={form.fat100g} onChange={set("fat100g")} /></div>
            <div className="field"><label htmlFor="carbs">Углеводы на 100 г</label><input id="carbs" inputMode="decimal" placeholder="значение" value={form.carbs100g} onChange={set("carbs100g")} /></div>
            <div className="field">
              <label htmlFor="calories">Калорийность на 100 г</label>
              <input id="calories" inputMode="decimal" placeholder="значение" value={form.calories100g} onChange={set("calories100g")} />
              <span className="field-hint">По Атуотеру: {fmt(atwater)} ккал</span>
            </div>
            <div className="field"><label htmlFor="code">Код (НСИ)</label><input id="code" placeholder="например ing_chicken_breast" value={form.code} onChange={set("code")} /></div>
            <div className="field"><label htmlFor="synonyms">Синонимы</label><input id="synonyms" placeholder="через запятую" value={form.synonyms} onChange={set("synonyms")} /></div>
          </div>
          <div className="field">
            <label>Связанные аллергены</label>
            <div className="checkbox-grid">
              {allergens.map((a) => (
                <label key={a.id}><input type="checkbox" checked={form.allergenIds.includes(a.id)} onChange={() => toggleIn("allergenIds", a.id)} />{a.name}</label>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Состав (для составного продукта)</label>
            <input placeholder="фильтр компонентов" value={componentSearch} onChange={(e) => setComponentSearch(e.target.value)} />
            {form.componentIds.length > 0 && (
              <div className="pill-row">
                {form.componentIds.map((id) => (
                  <button type="button" key={id} className="tag purple" style={{ cursor: "pointer" }} onClick={() => toggleIn("componentIds", id)} title="Убрать">
                    {ingredients.find((i) => i.id === id)?.name} ✕
                  </button>
                ))}
              </div>
            )}
            <div className="checkbox-grid scroll">
              {componentOptions.slice(0, 60).map((i) => (
                <label key={i.id}><input type="checkbox" checked={form.componentIds.includes(i.id)} onChange={() => toggleIn("componentIds", i.id)} />{i.name}</label>
              ))}
            </div>
          </div>
          <div className="field"><label htmlFor="composition">Описание состава</label><input id="composition" value={form.compositionDescription} onChange={set("compositionDescription")} /></div>
          <ErrorBox error={error} />
          <div className="inline">
            <Button type="submit" className="primary" busy={busy}>Сохранить ингредиент</Button>
            {form.id && <Button onClick={() => setForm(EMPTY_INGREDIENT)}>Отмена</Button>}
          </div>
        </form>
      </Panel>
    </>
  );
}

// ---------------- простые справочники ----------------

function DictionaryTab({ title, endpoint, adminEndpoint, fields, columns, onChanged, entityName }) {
  const notify = useToast();
  const items = useLoad(() => api(endpoint));
  const empty = Object.fromEntries(fields.map((f) => [f.key, ""]));
  const [form, setForm] = useState({ id: null, ...empty });
  const [error, setError] = useState(null);

  const save = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(fields.map((f) => [f.key, f.list ? splitList(form[f.key]) : form[f.key].trim() || null]));
    if (!body.name) return setError(new Error("Укажите название"));
    setError(null);
    try {
      if (form.id) await api(`${adminEndpoint}/${form.id}`, { method: "PUT", body });
      else await api(adminEndpoint, { method: "POST", body });
      notify(`${entityName} ${form.id ? "обновлён(а)" : "добавлен(а)"}`);
      setForm({ id: null, ...empty });
      items.reload();
      onChanged();
    } catch (err) {
      setError(err);
    }
  };

  const remove = async (item) => {
    if (!window.confirm(`Удалить «${item.name}»?`)) return;
    try {
      await api(`${adminEndpoint}/${item.id}`, { method: "DELETE" });
      notify(`${entityName} удалён(а)`);
      items.reload();
      onChanged();
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const edit = (item) => setForm({ id: item.id, ...Object.fromEntries(fields.map((f) => [f.key, f.list ? (item[f.key] || []).join(", ") : item[f.key] || ""])) });

  return (
    <section className="layout grid-2-wide">
      <Panel title={title} hint={`записей: ${items.data?.length ?? "…"}`}>
        {items.loading && !items.data ? <Loading /> : (
          <div className="table-wrap">
            <table style={{ minWidth: 420 }}>
              <thead><tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}<th>Действия</th></tr></thead>
              <tbody>
                {(items.data || []).map((item) => (
                  <tr key={item.id} className={form.id === item.id ? "selected" : ""}>
                    {columns.map(([render, label]) => <td key={label}>{render(item)}</td>)}
                    <td><div className="table-actions">
                      <button type="button" className="btn small" onClick={() => edit(item)}>Изменить</button>
                      <button type="button" className="btn small" onClick={() => remove(item)}>Удалить</button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel title={form.id ? "Редактирование" : "Новая запись"} hint={entityName}>
        <form className="form" onSubmit={save}>
          {fields.map((f) => (
            <div className="field" key={f.key}>
              <label htmlFor={`dict-${f.key}`}>{f.label}</label>
              {f.textarea
                ? <textarea id={`dict-${f.key}`} value={form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} placeholder={f.placeholder} />
                : <input id={`dict-${f.key}`} value={form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} placeholder={f.placeholder} />}
            </div>
          ))}
          <ErrorBox error={error} />
          <div className="inline">
            <Button type="submit" className="primary">Сохранить</Button>
            {form.id && <Button onClick={() => setForm({ id: null, ...empty })}>Отмена</Button>}
          </div>
        </form>
      </Panel>
    </section>
  );
}

function CategoriesTab({ onChanged }) {
  return (
    <DictionaryTab
      title="Справочник категорий ингредиентов" endpoint="/categories" adminEndpoint="/admin/categories" entityName="Категория" onChanged={onChanged}
      fields={[{ key: "name", label: "Наименование" }, { key: "code", label: "Код", placeholder: "cat_..." }, { key: "description", label: "Описание", textarea: true }]}
      columns={[[(c) => c.code || "—", "Код"], [(c) => c.name, "Наименование"], [(c) => c.ingredientsCount, "Ингредиентов"]]}
    />
  );
}

function AllergensTab({ onChanged }) {
  return (
    <DictionaryTab
      title="Справочник аллергенов" endpoint="/allergens" adminEndpoint="/admin/allergens" entityName="Аллерген" onChanged={onChanged}
      fields={[
        { key: "name", label: "Наименование" }, { key: "code", label: "Код", placeholder: "allergen_..." },
        { key: "description", label: "Описание", textarea: true }, { key: "synonyms", label: "Синонимы для нормализации", placeholder: "через запятую", list: true },
      ]}
      columns={[[(a) => a.code || "—", "Код"], [(a) => a.name, "Наименование"], [(a) => (a.synonyms || []).join(", ") || "—", "Синонимы"]]}
    />
  );
}

// ---------------- логи ----------------

const LOG_FILTERS = [
  ["", "Все события"],
  ["login_success,login_failed,login_locked,logout,register", "Входы и регистрация"],
  ["login_failed,login_locked", "Неудачные входы"],
  ["recipe_generate", "Генерация рецептов"],
  ["admin_user_update,admin_user_delete,admin_ingredient_create,admin_ingredient_update,admin_ingredient_delete,admin_allergen_create,admin_allergen_update,admin_allergen_delete,admin_category_create,admin_category_update,admin_category_delete", "Действия администратора"],
  ["backup_create,backup_restore", "Резервное копирование"],
];

function LogTable({ logs, compact = false }) {
  return (
    <div className="table-wrap">
      <table style={{ minWidth: compact ? 520 : 720 }}>
        <thead><tr><th>Время</th>{!compact && <th>Пользователь</th>}<th>Событие</th><th>Детали</th>{!compact && <th>IP</th>}</tr></thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td className="nowrap">{fmtDateTime(l.createdAt)}</td>
              {!compact && <td>{l.userEmail || l.details?.email || "—"}</td>}
              <td>{l.actionTitle}</td>
              <td className="small">{Object.entries(l.details || {}).filter(([, v]) => v !== null && v !== "").map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("; ") || "—"}</td>
              {!compact && <td className="small">{l.ip || "—"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LogsTab() {
  const [action, setAction] = useState("");
  const logs = useLoad(() => api("/admin/logs", { params: { action, limit: 300 } }), [action]);
  return (
    <Panel title="Журнал событий системы" actions={(
      <div className="toolbar-right">
        <select value={action} onChange={(e) => setAction(e.target.value)} aria-label="Тип событий">
          {LOG_FILTERS.map(([v, l]) => <option key={l} value={v}>{l}</option>)}
        </select>
        <Button className="small" onClick={logs.reload}>Обновить</Button>
      </div>
    )}>
      {logs.loading && !logs.data ? <Loading /> : logs.data?.length ? <LogTable logs={logs.data} /> : <Empty>Событий нет</Empty>}
    </Panel>
  );
}

// ---------------- резервные копии ----------------

const fmtSize = (b) => (b > 1048576 ? `${fmt(b / 1048576, 1)} МБ` : `${fmt(b / 1024, 0)} КБ`);

function BackupsTab({ onCreate, busy, onRestore }) {
  const backups = useLoad(() => api("/admin/backups"));
  return (
    <Panel title="Резервные копии базы данных" actions={(
      <div className="inline">
        <Button className="small" onClick={backups.reload}>Обновить список</Button>
        <Button className="small" onClick={onRestore}>Восстановить</Button>
        <Button className="small primary" busy={busy} onClick={async () => { await onCreate(); setTimeout(backups.reload, 2500); }}>Создать копию</Button>
      </div>
    )}>
      <Message kind="info">
        Ежедневная полная копия создаётся автоматически утилитой pg_dump по расписанию cron; копии старше 30 дней удаляются.
        Здесь можно запустить внеплановое копирование или восстановить базу из выбранной копии.
      </Message>
      <div className="mt-16">
        {backups.loading && !backups.data ? <Loading /> : !backups.data?.length ? <Empty>Резервных копий пока нет</Empty> : (
          <div className="table-wrap">
            <table style={{ minWidth: 480 }}>
              <thead><tr><th>Файл</th><th>Тип</th><th>Размер</th><th>Создан</th></tr></thead>
              <tbody>
                {backups.data.map((b) => (
                  <tr key={b.fileName}>
                    <td>{b.fileName}</td>
                    <td><span className={`tag ${b.fileName.includes("_auto") ? "teal" : "blue"}`}>{b.fileName.includes("_auto") ? "по расписанию" : "ручная"}</span></td>
                    <td>{fmtSize(b.sizeBytes)}</td>
                    <td>{fmtDateTime(b.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  );
}

function RestoreModal({ onClose, onDone }) {
  const notify = useToast();
  const backups = useLoad(() => api("/admin/backups"));
  const [file, setFile] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const restore = async () => {
    if (!file) return;
    if (!window.confirm(`Восстановить базу данных из «${file}»? Текущие данные будут заменены данными копии.`)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api("/admin/backups/restore", { method: "POST", body: { fileName: file } });
      notify(res.message);
      onDone();
      onClose();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Восстановление из резервной копии" onClose={onClose} footer={(
      <>
        <Button onClick={onClose}>Отмена</Button>
        <Button className="danger" busy={busy} disabled={!file} onClick={restore}>Восстановить</Button>
      </>
    )}>
      {backups.loading ? <Loading /> : !backups.data?.length ? <Empty>Нет доступных резервных копий</Empty> : (
        <div className="field">
          <label htmlFor="backup-file">Резервная копия</label>
          <select id="backup-file" value={file} onChange={(e) => setFile(e.target.value)}>
            <option value="">Выберите файл</option>
            {backups.data.map((b) => <option key={b.fileName} value={b.fileName}>{b.fileName} · {fmtDateTime(b.createdAt)} · {fmtSize(b.sizeBytes)}</option>)}
          </select>
        </div>
      )}
      <div className="mt-16"><Message kind="warn">Восстановление заменяет все таблицы базы данных состоянием на момент создания копии. Пользователи могут потребоваться повторно войти.</Message></div>
      {error && <div className="mt-16"><ErrorBox error={error} /></div>}
    </Modal>
  );
}

// ---------------- целостность ----------------

function IntegrityTab() {
  const issues = useLoad(() => api("/admin/integrity"));
  return (
    <Panel title="Мониторинг корректности и целостности данных" actions={<Button className="small" onClick={issues.reload}>Проверить снова</Button>}>
      {issues.loading && !issues.data ? <Loading /> : !issues.data?.length ? (
        <Message kind="ok">Ошибок не найдено: справочники согласованы, пищевая ценность корректна, составные продукты имеют состав.</Message>
      ) : (
        <div className="list">
          {issues.data.map((i, n) => (
            <div className="row-item" key={n}>
              <div className="row-main"><strong>{i.message}</strong><span>{i.entity}</span></div>
              <span className={`tag ${i.severity === "error" ? "red" : "amber"}`}>{i.severity === "error" ? "ошибка" : "предупреждение"}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
