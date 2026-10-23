import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Button, Empty, ErrorBox, Loading, Message, Metric, PageHeader, Panel, useLoad, useToast } from "../components/ui.jsx";
import { fmt } from "../format.js";

function toSelection(available) {
  return Object.fromEntries(available.map((a) => [a.ingredientId, a.availableQtyG ? String(a.availableQtyG) : ""]));
}

export default function Ingredients() {
  const notify = useToast();
  const data = useLoad(async () => {
    const [catalog, categories, available] = await Promise.all([api("/ingredients"), api("/categories"), api("/available-ingredients")]);
    return { catalog, categories, available };
  });
  const [selected, setSelected] = useState({});
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [onlyAllowed, setOnlyAllowed] = useState(false);
  const [onlySelected, setOnlySelected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (data.data) setSelected(toSelection(data.data.available));
  }, [data.data?.available]); // eslint-disable-line react-hooks/exhaustive-deps

  const catalog = data.data?.catalog || [];
  const byId = useMemo(() => Object.fromEntries(catalog.map((i) => [i.id, i])), [catalog]);
  const saved = useMemo(() => toSelection(data.data?.available || []), [data.data?.available]);
  const dirty = JSON.stringify(Object.entries(selected).sort()) !== JSON.stringify(Object.entries(saved).sort());

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase().replace("ё", "е");
    return catalog.filter((i) =>
      (!category || i.categoryId === category) &&
      (!onlyAllowed || i.isAllowed) &&
      (!onlySelected || i.id in selected) &&
      (!q || i.name.toLowerCase().replace("ё", "е").includes(q) || i.synonyms.some((s) => s.toLowerCase().includes(q))));
  }, [catalog, category, onlyAllowed, onlySelected, search, selected]);

  if (data.loading && !data.data) return <Loading />;
  if (data.error) return <ErrorBox error={data.error} />;

  const toggle = (item) => {
    setSelected((s) => {
      const next = { ...s };
      if (item.id in next) delete next[item.id];
      else next[item.id] = "";
      return next;
    });
  };

  const selectedIds = Object.keys(selected).filter((id) => byId[id]);
  const forbiddenSelected = selectedIds.filter((id) => !byId[id].isAllowed);
  const allowedSelected = selectedIds.filter((id) => byId[id].isAllowed);
  const categoriesInSet = new Set(allowedSelected.map((id) => byId[id].categoryId)).size;
  const notAllowed = catalog.filter((i) => !i.isAllowed).length;

  const save = async () => {
    const invalid = allowedSelected.filter((id) => selected[id] && !(Number(selected[id].replace(",", ".")) > 0));
    if (invalid.length) {
      setError(new Error(`Количество должно быть положительным числом: ${invalid.map((id) => byId[id].name).join(", ")}`));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const items = allowedSelected.map((id) => ({
        ingredientId: id,
        availableQtyG: selected[id] ? Number(selected[id].replace(",", ".")) : null,
      }));
      const available = await api("/available-ingredients", { method: "PUT", body: { items } });
      data.setData((d) => ({ ...d, available }));
      notify(`Набор сохранён: ${items.length} ингредиентов${forbiddenSelected.length ? `, исключено запрещённых: ${forbiddenSelected.length}` : ""}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Каталог и доступные ингредиенты" subtitle="Пищевая ценность указана на 100 г продукта.">
        <Button onClick={() => setSelected(saved)} disabled={!dirty}>Отменить изменения</Button>
        <Button className="primary" busy={busy} onClick={save} disabled={!dirty && forbiddenSelected.length === 0}>Сохранить набор</Button>
      </PageHeader>

      {error && <div style={{ marginBottom: 16 }}><ErrorBox error={error} /></div>}
      {forbiddenSelected.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Message kind="warn">
            В сохранённом наборе есть запрещённые ингредиенты: {forbiddenSelected.map((id) => byId[id].name).join(", ")}. При сохранении они будут исключены.
          </Message>
        </div>
      )}

      <Panel
        title="Каталог продуктов"
        actions={(
          <div className="toolbar-right">
            <input className="search" placeholder="поиск по названию" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Поиск" />
            <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Категория">
              <option value="">Все категории</option>
              {data.data.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <label className="checkbox-row small"><input type="checkbox" checked={onlyAllowed} onChange={(e) => setOnlyAllowed(e.target.checked)} />только допустимые</label>
            <label className="checkbox-row small"><input type="checkbox" checked={onlySelected} onChange={(e) => setOnlySelected(e.target.checked)} />только выбранные</label>
          </div>
        )}
      >
        {visible.length === 0 ? <Empty>Ничего не найдено</Empty> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Выбор</th><th>Ингредиент</th><th>Категория</th><th>Белки</th><th>Жиры</th><th>Углеводы</th><th>Ккал</th><th>Аллергены</th><th>Доступно, г</th></tr>
              </thead>
              <tbody>
                {visible.map((i) => {
                  const isSelected = i.id in selected;
                  return (
                    <tr key={i.id} className={`${isSelected ? "selected" : ""} ${!i.isAllowed ? "disabled" : ""}`}>
                      <td>
                        <input type="checkbox" checked={isSelected} disabled={!i.isAllowed && !isSelected}
                               onChange={() => toggle(i)} aria-label={`Выбрать ${i.name}`} title={i.violationReasons.join("; ")} />
                      </td>
                      <td>
                        {i.name}
                        {i.isComposite && <span className="tag purple" style={{ marginLeft: 6 }} title={i.components.map((c) => c.name).join(", ")}>составной</span>}
                        {!i.isAllowed && <div className="small" style={{ color: "var(--red)", marginTop: 4 }}>{i.violationReasons[0]}</div>}
                      </td>
                      <td>{i.categoryName || "—"}</td>
                      <td>{fmt(i.protein100g, 1)}</td>
                      <td>{fmt(i.fat100g, 1)}</td>
                      <td>{fmt(i.carbs100g, 1)}</td>
                      <td>{fmt(i.calories100g)}</td>
                      <td>
                        {i.effectiveAllergens.length === 0 ? <span className="tag green">нет</span>
                          : i.effectiveAllergens.map((a) => <span key={a.id} className={`tag ${i.isAllowed ? "amber" : "red"}`}>{a.name}</span>)}
                      </td>
                      <td>
                        {isSelected && i.isAllowed && (
                          <input className="input-sm" inputMode="decimal" placeholder="без огр." value={selected[i.id]}
                                 onChange={(e) => setSelected({ ...selected, [i.id]: e.target.value })} aria-label={`Количество ${i.name}`} />
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <section className="layout grid-3 mt-18">
        <Metric label="Выбрано ингредиентов" value={allowedSelected.length} hint={dirty ? "есть несохранённые изменения" : "набор сохранён"} />
        <Metric label="Недопустимых после запретов" value={notAllowed} hint={<Link className="btn link" to="/restrictions">к запретам</Link>} />
        <Metric label="Категорий в наборе" value={categoriesInSet} hint={allowedSelected.length >= 3 ? <Link className="btn link" to="/generate">перейти к генерации</Link> : "для генерации нужно не менее 3 ингредиентов"} />
      </section>
    </>
  );
}
