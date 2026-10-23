import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api.js";
import RecipeView from "../components/RecipeView.jsx";
import { Button, ErrorBox, Loading, Message, PageHeader, Panel, useLoad, useToast } from "../components/ui.jsx";
import { fmt, MEAL_SHARES, MEAL_TYPES, nearestShare, SOURCE } from "../format.js";

const DRAFT_KEY = "grsn.generateDraft";

function readDraft() {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY)) || null;
  } catch {
    return null;
  }
}

export default function Generate() {
  const notify = useToast();
  const location = useLocation();
  const data = useLoad(async () => {
    const [goals, profile, available] = await Promise.all([api("/goals"), api("/profile"), api("/available-ingredients")]);
    return { goals, profile, available };
  });
  const [form, setForm] = useState(() => {
    const draft = { goalId: "", mealType: "", variantsCount: 1, mealShare: 0.333, difficulty: "", comment: "", ...readDraft() };
    return { ...draft, mealShare: nearestShare(Number(draft.mealShare)) };
  });
  const [result, setResult] = useState(null);
  const [active, setActive] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dietBusy, setDietBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!data.data) return;
    const preset = location.state?.goalId;
    setForm((f) => ({ ...f, goalId: preset || f.goalId || data.data.profile.goal?.id || "" }));
  }, [data.data, location.state]);

  if (data.loading && !data.data) return <Loading />;
  if (data.error) return <ErrorBox error={data.error} />;
  const { goals, profile, available } = data.data;
  const goal = goals.find((g) => g.id === form.goalId);
  const dayTarget = profile.tdee && goal ? profile.tdee + goal.calorieDelta : null;
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const saveDraft = () => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
      notify("Черновик параметров сохранён");
    } catch {
      notify("Не удалось сохранить черновик", "error");
    }
  };

  const generate = async () => {
    if (!form.goalId) {
      setError(new Error("Выберите фитнес-ориентир"));
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await api("/recipes/generate", {
        method: "POST",
        body: {
          goalId: form.goalId,
          variantsCount: Number(form.variantsCount),
          mealShare: Number(form.mealShare),
          difficulty: form.difficulty || null,
          comment: form.comment.trim() || null,
          mealType: form.mealType || null,
        },
      });
      setResult(response);
      setActive(0);
      if (response.status === "generated") {
        notify(`Сформировано вариантов: ${response.recipes.length}. Нажмите «Добавить в рацион» у рецепта, который будете готовить`);
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const recipe = result?.recipes?.[active];

  // Только рецепты, включённые в рацион, учитываются в отчётах и анализе
  const toggleDiet = async () => {
    setDietBusy(true);
    try {
      const updated = await api(`/recipes/${recipe.id}/diet`, { method: recipe.inDiet ? "DELETE" : "POST" });
      setResult((r) => ({ ...r, recipes: r.recipes.map((x) => (x.id === updated.id ? updated : x)) }));
      notify(updated.inDiet ? "Рецепт добавлен в рацион — он будет учтён в отчётах и анализе" : "Рецепт убран из рациона, но остался в истории");
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setDietBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Генерация рецепта" subtitle="Формирование вариантов с последующей проверкой пищевой ценности и запретов.">
        <Button onClick={saveDraft}>Сохранить черновик</Button>
        <Button className="primary" busy={busy} onClick={generate} disabled={!profile.weightKg}>
          {busy ? "Генерация…" : "Сгенерировать"}
        </Button>
      </PageHeader>

      {!profile.weightKg && (
        <div style={{ marginBottom: 16 }}>
          <Message kind="warn">Для генерации заполните <Link className="btn link" to="/profile">профиль</Link>: вес, рост, возраст, пол и уровень активности.</Message>
        </div>
      )}
      {profile.weightKg && available.length < 3 && (
        <div style={{ marginBottom: 16 }}>
          <Message kind="warn">В наборе доступных ингредиентов {available.length} поз. — <Link className="btn link" to="/ingredients">добавьте ингредиенты</Link> (нужно не менее трёх).</Message>
        </div>
      )}

      <section className="split">
        <Panel title="1. Параметры генерации" hint="Запрос генерации">
          <form className="form" onSubmit={(e) => { e.preventDefault(); generate(); }}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="goal">Фитнес-ориентир</label>
                <select id="goal" value={form.goalId} onChange={set("goalId")}>
                  <option value="">Выберите фитнес-ориентир</option>
                  {goals.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="meal-type">Приём пищи</label>
                <select id="meal-type" value={form.mealType} onChange={(e) => {
                  const meal = MEAL_TYPES.find((m) => m.value === e.target.value);
                  setForm({ ...form, mealType: e.target.value, mealShare: meal ? meal.share : form.mealShare });
                }}>
                  <option value="">Не указан</option>
                  {MEAL_TYPES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                <span className="field-hint">Для завтрака и перекуса модели передаются только подходящие продукты</span>
              </div>
              <div className="field">
                <label htmlFor="variants">Количество вариантов</label>
                <select id="variants" value={form.variantsCount} onChange={set("variantsCount")}>
                  <option value={1}>Один вариант</option>
                  <option value={2}>Два варианта</option>
                  <option value={3}>Три варианта</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="meal">Сколько суточной нормы калорий занимает блюдо</label>
                <select id="meal" value={form.mealShare} onChange={set("mealShare")}>
                  {MEAL_SHARES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
                {dayTarget && <span className="field-hint">Цель приёма пищи: ≈ {fmt(dayTarget * form.mealShare)} ккал из {fmt(dayTarget)} ккал/день</span>}
              </div>
              <div className="field">
                <label htmlFor="difficulty">Сложность</label>
                <select id="difficulty" value={form.difficulty} onChange={set("difficulty")}>
                  <option value="">Любая</option>
                  <option value="low">Низкая</option>
                  <option value="medium">Средняя</option>
                  <option value="high">Высокая</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="comment">Дополнительные пожелания</label>
              <textarea id="comment" maxLength={500} placeholder="например: без духовки, побыстрее, поострее" value={form.comment} onChange={set("comment")} />
            </div>
            <button type="submit" hidden />
          </form>
        </Panel>

        {busy && <Panel><Loading text="Модель формирует рецепт и проверяет его по БЖУ, калорийности и запретам…" /></Panel>}
        <ErrorBox error={error} />

        {result?.status === "failed" && (
          <Panel title="2. Результат генерации" actions={<span className="status bad">рецепт не сформирован</span>}>
            <div className="stack">
              <Message kind="error" title={result.failureReason}>
                {result.conflicts.length > 0 && <ul>{result.conflicts.map((c) => <li key={c}>{c}</li>)}</ul>}
              </Message>
              {result.recommendedIngredients.length > 0 && (
                <div>
                  <strong>Рекомендуемые ингредиенты для допустимого рецепта:</strong>
                  <div className="pill-row mt-16">{result.recommendedIngredients.map((r) => <span key={r} className="tag green">{r}</span>)}</div>
                </div>
              )}
              {result.suggestions.length > 0 && (
                <Message kind="info" title="Что можно сделать">
                  <ul>{result.suggestions.map((s) => <li key={s}>{s}</li>)}</ul>
                  <div className="inline mt-16">
                    <Link className="btn small" to="/ingredients">Изменить набор ингредиентов</Link>
                    <Link className="btn small" to="/profile">Изменить цель</Link>
                  </div>
                </Message>
              )}
            </div>
          </Panel>
        )}

        {result?.status === "generated" && (
          <>
            <div className="inline">
              {result.recipes.length > 1 && (
                <div className="tabs">
                  {result.recipes.map((r, i) => (
                    <button type="button" key={r.id} className={`tab ${i === active ? "active" : ""}`} onClick={() => setActive(i)}>
                      Вариант {i + 1}{r.inDiet ? " ✓" : ""}
                    </button>
                  ))}
                </div>
              )}
              <span className="muted small">
                Модель: {SOURCE[result.provider] || result.provider} · время ответа {fmt(result.durationMs / 1000, 1)} с
              </span>
            </div>
            {result.warnings.length > 0 && <Message kind="warn"><ul style={{ margin: 0 }}>{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul></Message>}
            {!result.recipes.some((r) => r.inDiet) && (
              <Message kind="info">
                Рецепты сохранены в историю. В отчёты и анализ попадут только те, что вы добавите в рацион, — выберите вариант,
                который будете готовить, и нажмите «Добавить в рацион».
              </Message>
            )}
            {recipe && <RecipeView recipe={recipe} numbered onToggleDiet={toggleDiet} dietBusy={dietBusy} />}
          </>
        )}
      </section>
    </>
  );
}
