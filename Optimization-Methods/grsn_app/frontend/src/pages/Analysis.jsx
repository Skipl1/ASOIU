import { useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Button, CHART_COLORS, ErrorBox, Loading, Message, Metric, PageHeader, Panel, useLoad } from "../components/ui.jsx";
import { daysAgo, fmt, fmtDate, fmtSigned, isoDate, PRIORITY } from "../format.js";

const ROWS = [["calories", "Калорийность", "ккал"], ["protein", "Белки", "г"], ["fat", "Жиры", "г"], ["carbs", "Углеводы", "г"]];

function deviationTag(pct) {
  const a = Math.abs(pct);
  const cls = a <= 10 ? "ok" : a <= 20 ? "warn" : "bad";
  return <span className={`status ${cls}`}>{fmtSigned(pct, 0)} %</span>;
}

export default function Analysis() {
  const [period, setPeriod] = useState({ dateFrom: daysAgo(6), dateTo: daysAgo(0) });
  const [query, setQuery] = useState(period);
  const [showPeriod, setShowPeriod] = useState(false);
  const analysis = useLoad(() => api("/analysis/nutrition", { params: query }), [query]);

  const preset = (days) => {
    const next = { dateFrom: daysAgo(days - 1), dateTo: daysAgo(0) };
    setPeriod(next);
    setQuery(next);
  };

  const a = analysis.data;
  // Ось X — все дни периода; расчётная линия есть только при данных минимум за 3 дня, замеры — когда они вносились
  const chart = [];
  if (a) {
    const calc = Object.fromEntries(a.calculatedWeightTrend.map((p) => [p.date, p.weightKg]));
    const measured = Object.fromEntries(a.measuredWeights.map((m) => [m.date, m.weightKg]));
    for (let d = new Date(`${a.dateFrom}T00:00:00`); isoDate(d) <= a.dateTo; d.setDate(d.getDate() + 1)) {
      const key = isoDate(d);
      chart.push({ date: fmtDate(key), calc: calc[key] ?? null, measured: measured[key] ?? null });
    }
  }
  const kg = (v, digits) => (v === null || v === undefined ? "—" : `${fmt(v, digits)} кг`);

  return (
    <>
      <PageHeader title="Анализ соответствия рациона цели" subtitle="Сравнение фактической пищевой ценности рецептов с целевыми значениями пользователя.">
        <Button onClick={() => setShowPeriod((v) => !v)}>{fmtDate(query.dateFrom)} — {fmtDate(query.dateTo)}</Button>
        <Button className="primary" onClick={() => setQuery({ ...period })}>Обновить анализ</Button>
      </PageHeader>

      {showPeriod && (
        <Panel title="Выбранный период" actions={(
          <div className="inline">
            <Button className="small" onClick={() => preset(7)}>7 дней</Button>
            <Button className="small" onClick={() => preset(14)}>14 дней</Button>
            <Button className="small" onClick={() => preset(30)}>30 дней</Button>
          </div>
        )} style={{ marginBottom: 16 }}>
          <div className="form-grid">
            <div className="field"><label htmlFor="from">Начало</label><input id="from" type="date" value={period.dateFrom} onChange={(e) => setPeriod({ ...period, dateFrom: e.target.value })} /></div>
            <div className="field"><label htmlFor="to">Конец</label><input id="to" type="date" value={period.dateTo} onChange={(e) => setPeriod({ ...period, dateTo: e.target.value })} /></div>
          </div>
        </Panel>
      )}

      {analysis.error && (
        <Message kind={analysis.error.status === 400 ? "warn" : "error"}>
          {analysis.error.message}
          {analysis.error.status === 400 && <> — <Link className="btn link" to="/profile">перейти в профиль</Link></>}
        </Message>
      )}
      {analysis.loading && !a ? <Loading /> : a && (
        <>
          <Panel title="1. Исходные данные анализа" hint="Профиль + история рецептов">
            <div className="table-wrap">
              <table style={{ minWidth: 420 }}>
                <thead><tr><th>Показатель</th><th>Значение</th></tr></thead>
                <tbody>
                  <tr><td>Фитнес-ориентир</td><td>{a.goalName}</td></tr>
                  <tr><td>Целевая калорийность дня</td><td>{fmt(a.targetCaloriesDay)} ккал</td></tr>
                  <tr><td>Рецептов в рационе</td><td>{a.recipesAnalyzed} (дней с данными: {a.daysWithData})</td></tr>
                  <tr><td>Запрещённые продукты</td><td>{a.restrictionsCount} огранич. · нарушений: {a.violationsFound}</td></tr>
                  <tr><td>Пользовательские оценки</td><td>{a.averageRating ? `${fmt(a.averageRating, 1)} из 5 (${a.ratingsCount})` : "нет оценок"}</td></tr>
                </tbody>
              </table>
            </div>
          </Panel>

          <section className="layout grid-3 mt-16">
            <Metric label="Соответствие цели" value={`${fmt(a.complianceScore)} / 100`} hint="интегральная оценка по отклонениям" />
            <Metric label="Факт, ккал в день" value={fmt(a.actual.calories)} hint={`цель ${fmt(a.target.calories)}`} />
            <Metric label="Прогноз веса через 30 дней" value={kg(a.forecastWeight30dKg, 1)}
                    hint={a.trendSufficient ? "при сохранении текущего рациона" : "нужны рецепты в рационе минимум за 3 дня"} />
          </section>

          <Panel className="mt-16" title="2. Сравнение факта с целью" hint="среднее в день за выбранный период">
            <div className="table-wrap">
              <table style={{ minWidth: 520 }}>
                <thead><tr><th>Показатель</th><th>Цель</th><th>Факт</th><th>Отклонение</th></tr></thead>
                <tbody>
                  {ROWS.map(([key, label, unit]) => (
                    <tr key={key}>
                      <td>{label}</td>
                      <td>{fmt(a.target[key])} {unit}</td>
                      <td>{fmt(a.actual[key])} {unit}</td>
                      <td>{a.daysWithData ? <span className="inline">{fmtSigned(a.deviation[key])} {unit} {deviationTag(a.deviationPercent[key])}</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel className="mt-16" title="3. Тренд веса за выбранный период" hint="расчёт по калорийности рецептов">
            <div className="trend-panel">
              <div className="forecast-summary">
                <div><span>Вес на начало периода</span><strong>{kg(a.startWeightKg, 1)}</strong></div>
                <div><span>Расчётный вес на конец периода</span><strong>{kg(a.endWeightKg, 2)}</strong></div>
                <div><span>Прогноз по питанию, скорость</span><strong>{a.calculatedTrendKgPerWeek != null ? `${fmtSigned(a.calculatedTrendKgPerWeek, 2)} кг/нед` : "—"}</strong></div>
                <div><span>По замерам веса, скорость</span><strong>{a.measuredTrendKgPerWeek !== null ? `${fmtSigned(a.measuredTrendKgPerWeek, 2)} кг/нед` : "—"}</strong></div>
              </div>
              <p className="muted trend-note">
                <b>Прогноз по питанию</b> — как должен меняться вес при таком рационе: съеденные калории минус расход (7700 ккал ≈ 1 кг).
                {a.weightChangeKg != null && <> За выбранный период это {fmtSigned(a.weightChangeKg, 2)} кг.</>}{" "}
                <b>По замерам</b> — как вес менялся на самом деле по вашим взвешиваниям. Если цифры близки, рацион работает как задумано; если расходятся, на вес влияют вода, тренировки или неточность взвешивания.
              </p>
              {!a.trendSufficient && (
                <Message kind="info">
                  Расчётный тренд и прогноз по калориям не строятся: в рационе есть рецепты за {a.daysWithData} {a.daysWithData === 1 ? "день" : "дня"},
                  а нужно минимум за 3 дня. Добавляйте рецепты в рацион на страницах «Генерация» и «История». Показаны только фактические замеры веса.
                </Message>
              )}
              <div className="chart-box">
                <ResponsiveContainer>
                  <ComposedChart data={chart} margin={{ top: 10, right: 16, left: -6, bottom: 0 }}>
                    <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={12} />
                    <YAxis stroke={CHART_COLORS.axis} fontSize={12} domain={["dataMin - 0.5", "dataMax + 0.5"]} tickFormatter={(v) => fmt(v, 1)} />
                    <Tooltip formatter={(v, n) => [`${fmt(v, 2)} кг`, n]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {a.trendSufficient && (
                      <Line isAnimationActive={false} name="Расчётный тренд веса" type="monotone" dataKey="calc" stroke={CHART_COLORS.line} strokeWidth={3} dot={false} />
                    )}
                    <Scatter isAnimationActive={false} name="Замеры" dataKey="measured" fill={CHART_COLORS.protein} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-legend" style={{ display: "grid", gap: 6 }}>
                <span>Расчётная линия: Δm = (E<sub>факт</sub> − TDEE) / 7700 ккал на кг за каждый день, в который в рационе есть рецепты; остальные дни не меняют вес.</span>
                <span>Точки — замеры веса из профиля (один на день). Это независимые источники: расчёт по калориям не учитывает воду и другие факторы, поэтому они могут расходиться.</span>
              </div>
            </div>
          </Panel>

          <Panel className="mt-16" title="4. Рекомендации по корректировке" hint="на основе найденных отклонений">
            <div className="list">
              {a.recommendations.map((r) => {
                const [cls, label] = PRIORITY[r.priority];
                return (
                  <div className="row-item" key={r.text}>
                    <div className="row-main"><strong>{r.text}</strong><span>Основание: {r.reason}</span></div>
                    <span className={`tag ${cls}`}>{label}</span>
                  </div>
                );
              })}
            </div>
          </Panel>
        </>
      )}
    </>
  );
}
