import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { DIFFICULTY, fmt, fmtDateTime, fmtSigned, MEAL_LABEL, SOURCE } from "../format.js";
import { Button, CHART_COLORS, MacroBars, Message, Panel, StatusTag } from "./ui.jsx";

export function MacroPie({ protein, fat, carbs }) {
  const data = [
    { name: "Белки", value: protein * 4, color: CHART_COLORS.protein },
    { name: "Жиры", value: fat * 9, color: CHART_COLORS.fat },
    { name: "Углеводы", value: carbs * 4, color: CHART_COLORS.carbs },
  ];
  return (
    <div style={{ width: "100%", height: 200 }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie isAnimationActive={false} data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2} stroke="none">
            {data.map((d) => <Cell key={d.name} fill={d.color} />)}
          </Pie>
          <Tooltip formatter={(v, n) => [`${fmt(v)} ккал`, n]} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function RecipeView({ recipe, numbered = false, onToggleDiet, dietBusy = false }) {
  const pct = recipe.macroPercent || { protein: 0, fat: 0, carbs: 0 };
  const n = (i) => (numbered ? `${i}. ` : "");
  return (
    <div className="layout">
      <Panel title={`${n(2)}Результат генерации`} actions={
        <div className="inline">
          <span className={`status ${recipe.isAllowed ? "ok" : "bad"}`}>
            {recipe.isAllowed ? "соответствует запретам" : "нарушает запреты"}
          </span>
          {onToggleDiet && (recipe.inDiet
            ? <Button className="small" busy={dietBusy} onClick={onToggleDiet} title="Рецепт учитывается в отчётах и анализе">✓ В рационе — убрать</Button>
            : <Button className="small primary" busy={dietBusy} onClick={onToggleDiet} disabled={!recipe.isAllowed}
                      title="Только рецепты из рациона учитываются в отчётах и анализе">Добавить в рацион</Button>)}
        </div>
      }>
        <div className="recipe-visual">
          {recipe.name}
          <small>{recipe.goalName} · {fmtDateTime(recipe.createdAt)}{recipe.source ? ` · ${SOURCE[recipe.source] || recipe.source}` : ""}</small>
        </div>
        <div style={{ height: 14 }} />
        <div className="pill-row">
          {recipe.mealType && <span className="tag purple">{MEAL_LABEL[recipe.mealType]}</span>}
          {recipe.inDiet && <span className="tag green">в рационе</span>}
          <span className="tag blue">{recipe.servings} порц. по {fmt(recipe.servingMassG)} г</span>
          <span className="tag green">{fmt(recipe.caloriesTotal)} ккал</span>
          {recipe.cookingTimeMin && <span className="tag purple">{recipe.cookingTimeMin} мин</span>}
          {recipe.difficulty && <span className="tag teal">сложность: {DIFFICULTY[recipe.difficulty]?.toLowerCase()}</span>}
          {recipe.targetCalories && <span className="tag amber">цель {fmt(recipe.targetCalories)} ккал (δ {fmtSigned(recipe.deviationKcal)})</span>}
        </div>
        <div style={{ height: 16 }} />
        <div className="grid-2-wide" style={{ alignItems: "center" }}>
          <MacroBars protein={pct.protein} fat={pct.fat} carbs={pct.carbs}
                     grams={{ protein: recipe.proteinTotal, fat: recipe.fatTotal, carbs: recipe.carbsTotal }} />
          <MacroPie protein={recipe.proteinTotal} fat={recipe.fatTotal} carbs={recipe.carbsTotal} />
        </div>
      </Panel>

      <Panel title="Состав и пищевая ценность" hint="расчёт по формулам ТЗ 4.6">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Ингредиент</th><th>Категория</th><th>Масса, г</th><th>Белки</th><th>Жиры</th><th>Углеводы</th><th>Ккал</th></tr></thead>
            <tbody>
              {recipe.ingredients.map((i) => (
                <tr key={i.ingredientId}>
                  <td>{i.name}</td><td>{i.categoryName || "—"}</td><td>{fmt(i.massG)}</td>
                  <td>{fmt(i.protein, 1)}</td><td>{fmt(i.fat, 1)}</td><td>{fmt(i.carbs, 1)}</td><td>{fmt(i.calories)}</td>
                </tr>
              ))}
              <tr>
                <td><strong>Итого</strong></td><td /><td><strong>{fmt(recipe.ingredients.reduce((s, i) => s + i.massG, 0))}</strong></td>
                <td><strong>{fmt(recipe.proteinTotal, 1)}</strong></td><td><strong>{fmt(recipe.fatTotal, 1)}</strong></td>
                <td><strong>{fmt(recipe.carbsTotal, 1)}</strong></td><td><strong>{fmt(recipe.caloriesTotal)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title={`${n(3)}Проверка результата`} hint="После генерации">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Показатель</th><th>Состояние</th><th>Комментарий</th></tr></thead>
            <tbody>
              {recipe.checks.map((c) => (
                <tr key={c.indicator}><td>{c.indicator}</td><td><StatusTag status={c.status}>{c.label}</StatusTag></td><td>{c.comment}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title={`${n(4)}Инструкция приготовления`} hint="последовательность действий">
        <ol className="steps">
          {recipe.instructions.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
        {recipe.tips?.length > 0 && (
          <div className="mt-16">
            <Message kind="info" title="Рекомендации и замены">
              <ul>{recipe.tips.map((t) => <li key={t}>{t}</li>)}</ul>
            </Message>
          </div>
        )}
      </Panel>
    </div>
  );
}
