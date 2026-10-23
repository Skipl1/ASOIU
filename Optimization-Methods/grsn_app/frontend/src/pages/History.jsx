import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import RecipeView from "../components/RecipeView.jsx";
import { Button, Empty, ErrorBox, Loading, Metric, PageHeader, Panel, Stars, useLoad, useToast } from "../components/ui.jsx";
import { fmt, fmtDateTime, MEAL_LABEL } from "../format.js";

const SCORES = [[5, "5 — отлично"], [4, "4 — хорошо"], [3, "3 — нормально"], [2, "2 — плохо"], [1, "1 — очень плохо"]];

export default function History() {
  const notify = useToast();
  const navigate = useNavigate();
  const [filters, setFilters] = useState({ search: "", goalId: "", dateFrom: "", dateTo: "", inDiet: "" });
  const [showFilters, setShowFilters] = useState(false);
  const goals = useLoad(() => api("/goals"));
  const list = useLoad(() => api("/recipes", { params: filters }), [filters.goalId, filters.dateFrom, filters.dateTo, filters.search, filters.inDiet]);
  const [selectedId, setSelectedId] = useState(null);
  const [recipe, setRecipe] = useState(null);
  const [rating, setRating] = useState({ score: "", comment: "" });
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dietBusy, setDietBusy] = useState(null);
  const detailRef = useRef(null);

  useEffect(() => {
    if (!selectedId) return;
    api(`/recipes/${selectedId}`).then((r) => {
      setRecipe(r);
      setRating({ score: r.myRating?.score ? String(r.myRating.score) : "", comment: r.myRating?.comment || "" });
      setEdit(null);
    }).catch((err) => notify(err.message, "error"));
  }, [selectedId, notify]);

  const recipes = list.data || [];
  const rated = recipes.filter((r) => r.rating);
  const avg = rated.length ? rated.reduce((s, r) => s + r.rating, 0) / rated.length : null;

  const open = (id) => {
    setSelectedId(id);
    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 150);
  };

  const saveRating = async () => {
    if (!rating.score) {
      notify("Выберите оценку", "error");
      return;
    }
    setBusy(true);
    try {
      await api(`/recipes/${recipe.id}/rating`, { method: "POST", body: { score: Number(rating.score), comment: rating.comment || null } });
      notify("Оценка сохранена — она будет учтена при следующих генерациях");
      list.reload();
      setRecipe(await api(`/recipes/${recipe.id}`));
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async () => {
    const items = recipe.ingredients.map((i) => ({ ingredientId: i.ingredientId, massG: Number(String(edit[i.ingredientId]).replace(",", ".")) }));
    if (items.some((i) => !(i.massG > 0))) {
      notify("Масса должна быть положительным числом", "error");
      return;
    }
    setBusy(true);
    try {
      setRecipe(await api(`/recipes/${recipe.id}`, { method: "PATCH", body: { ingredients: items } }));
      setEdit(null);
      list.reload();
      notify("Рецепт обновлён, пищевая ценность пересчитана");
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Удалить рецепт «${recipe.name}» из истории?`)) return;
    await api(`/recipes/${recipe.id}`, { method: "DELETE" });
    setSelectedId(null);
    setRecipe(null);
    list.reload();
    notify("Рецепт удалён");
  };

  const setFilter = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });

  // Только рецепты, включённые в рацион, учитываются в отчётах и анализе
  const toggleDiet = async (item) => {
    setDietBusy(item.id);
    try {
      const updated = await api(`/recipes/${item.id}/diet`, { method: item.inDiet ? "DELETE" : "POST" });
      list.setData((rows) => rows.map((r) => (r.id === updated.id ? { ...r, inDiet: updated.inDiet } : r)));
      if (recipe?.id === updated.id) setRecipe(updated);
      notify(updated.inDiet ? "Рецепт добавлен в рацион" : "Рецепт убран из рациона, но остался в истории");
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setDietBusy(null);
    }
  };

  return (
    <>
      <PageHeader title="История рецептов и оценки" subtitle="Повторное обращение к ранее созданным рецептам.">
        <Button onClick={() => setShowFilters((v) => !v)}>{showFilters ? "Скрыть фильтр" : "Фильтр"}</Button>
        <Button className="primary" onClick={() => navigate("/generate", { state: { goalId: recipe?.goalId || filters.goalId || undefined } })}>
          Повторить генерацию
        </Button>
      </PageHeader>

      <section className="layout grid-4">
        <Metric label="Всего рецептов" value={recipes.length} />
        <Metric label="В рационе" value={recipes.filter((r) => r.inDiet).length} hint="учитываются в отчётах и анализе" />
        <Metric label="Средняя оценка" value={avg ? fmt(avg, 1) : "—"} hint={`оценено: ${rated.length}`} />
        <Metric label="Без нарушений" value={recipes.filter((r) => r.isAllowed).length} />
      </section>

      <Panel className="mt-18" title="Архив рецептов" actions={(
        <div className="toolbar-right">
          <input className="search" placeholder="поиск по названию" value={filters.search} onChange={setFilter("search")} aria-label="Поиск" />
          <select value={filters.inDiet} onChange={setFilter("inDiet")} aria-label="Рацион">
            <option value="">Все рецепты</option>
            <option value="true">В рационе</option>
            <option value="false">Не в рационе</option>
          </select>
          <select value={filters.goalId} onChange={setFilter("goalId")} aria-label="Цель">
            <option value="">Все цели</option>
            {(goals.data || []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </div>
      )}>
        {showFilters && (
          <div className="form-grid" style={{ marginBottom: 14 }}>
            <div className="field"><label htmlFor="from">С даты</label><input id="from" type="date" value={filters.dateFrom} onChange={setFilter("dateFrom")} /></div>
            <div className="field"><label htmlFor="to">По дату</label><input id="to" type="date" value={filters.dateTo} onChange={setFilter("dateTo")} /></div>
          </div>
        )}
        {list.error && <ErrorBox error={list.error} />}
        {list.loading && !list.data ? <Loading /> : recipes.length === 0 ? <Empty>Рецептов не найдено</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Дата</th><th>Рецепт</th><th>Цель</th><th>Ккал</th><th>БЖУ, г</th><th>Оценка</th><th>Рацион</th><th>Действия</th></tr></thead>
              <tbody>
                {recipes.map((r) => (
                  <tr key={r.id} className={r.id === selectedId ? "selected" : ""}>
                    <td className="nowrap">{fmtDateTime(r.createdAt)}</td>
                    <td>
                      {r.name}
                      {r.mealType && <span className="tag purple" style={{ marginLeft: 6 }}>{MEAL_LABEL[r.mealType]}</span>}
                      {!r.isAllowed && <span className="tag red" style={{ marginLeft: 6 }}>нарушение</span>}
                    </td>
                    <td>{r.goalName}</td>
                    <td>{fmt(r.caloriesTotal)}</td>
                    <td className="nowrap">{fmt(r.proteinTotal)} / {fmt(r.fatTotal)} / {fmt(r.carbsTotal)}</td>
                    <td><Stars score={r.rating} /></td>
                    <td>
                      <Button className={`small ${r.inDiet ? "" : "ghost"}`} busy={dietBusy === r.id} onClick={() => toggleDiet(r)}
                              title={r.inDiet ? "Убрать из рациона" : "Добавить в рацион"}>
                        {r.inDiet ? "✓ в рационе" : "+ в рацион"}
                      </Button>
                    </td>
                    <td><button type="button" className="btn small" onClick={() => open(r.id)}>Открыть</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div ref={detailRef} />
      {recipe && (
        <>
          <section className="layout grid-2-wide mt-18">
            <Panel title="Оценка выбранного рецепта" hint="Пользовательская обратная связь">
              <form className="form" onSubmit={(e) => { e.preventDefault(); saveRating(); }}>
                <div className="field">
                  <label htmlFor="score">Балл</label>
                  <select id="score" value={rating.score} onChange={(e) => setRating({ ...rating, score: e.target.value })}>
                    <option value="">Выберите оценку</option>
                    {SCORES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="comment">Комментарий</label>
                  <textarea id="comment" maxLength={1000} placeholder="комментарий пользователя" value={rating.comment}
                            onChange={(e) => setRating({ ...rating, comment: e.target.value })} />
                </div>
                <Button type="submit" className="primary" busy={busy}>Сохранить оценку</Button>
              </form>
            </Panel>
            <Panel title="Состав выбранного рецепта" actions={
              edit ? (
                <div className="inline">
                  <Button className="small" onClick={() => setEdit(null)}>Отмена</Button>
                  <Button className="small primary" busy={busy} onClick={saveEdit}>Сохранить</Button>
                </div>
              ) : (
                <div className="inline">
                  <Button className="small" onClick={() => setEdit(Object.fromEntries(recipe.ingredients.map((i) => [i.ingredientId, i.massG])))}>Редактировать</Button>
                  <Button className="small" onClick={remove}>Удалить</Button>
                </div>
              )
            }>
              <div className="list">
                {recipe.ingredients.map((i) => (
                  <div className="row-item" key={i.ingredientId}>
                    <div className="row-main"><strong>{i.name}</strong><span>{i.categoryName}</span></div>
                    {edit ? (
                      <input className="input-sm" inputMode="decimal" value={edit[i.ingredientId]} aria-label={`Масса ${i.name}`}
                             onChange={(e) => setEdit({ ...edit, [i.ingredientId]: e.target.value })} />
                    ) : <strong>{fmt(i.massG)} г</strong>}
                  </div>
                ))}
              </div>
            </Panel>
          </section>
          <div className="mt-18"><RecipeView recipe={recipe} onToggleDiet={() => toggleDiet(recipe)} dietBusy={dietBusy === recipe.id} /></div>
        </>
      )}
    </>
  );
}
