import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, downloadFile } from "../api.js";
import { Button, CHART_COLORS, Empty, ErrorBox, Loading, MacroBars, Metric, PageHeader, Panel, StatusTag, useLoad, useToast } from "../components/ui.jsx";
import { daysAgo, fmt, fmtDate, fmtDateTime, fmtSigned } from "../format.js";

const FORMAT_TAG = { pdf: "blue", xlsx: "purple", csv: "teal" };
const WEEKDAYS = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];

export default function Reports() {
  const notify = useToast();
  const [params, setParams] = useState({ dateFrom: daysAgo(6), dateTo: daysAgo(0), format: "pdf", goalId: "" });
  const [query, setQuery] = useState(params);
  const goals = useLoad(() => api("/goals"));
  const report = useLoad(() => api("/reports/nutrition", { params: { dateFrom: query.dateFrom, dateTo: query.dateTo, goalId: query.goalId } }), [query]);
  const saved = useLoad(() => api("/reports"));
  const [exporting, setExporting] = useState(null);

  const set = (key) => (e) => setParams({ ...params, [key]: e.target.value });
  const validPeriod = params.dateFrom && params.dateTo && params.dateFrom <= params.dateTo;

  const exportAs = async (format) => {
    if (!validPeriod) {
      notify("Проверьте период: дата начала должна быть не позже даты окончания", "error");
      return;
    }
    setExporting(format);
    try {
      const res = await api("/reports/nutrition/export", {
        method: "POST",
        body: { dateFrom: params.dateFrom, dateTo: params.dateTo, format, goalId: params.goalId || null },
      });
      await downloadFile(res.downloadUrl, res.fileName);
      saved.reload();
      notify(`Отчёт ${format.toUpperCase()} сформирован и сохранён в истории`);
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setExporting(null);
    }
  };

  const r = report.data;
  const chart = (r?.dailyCalories || []).map((d) => ({
    label: r.dailyCalories.length <= 7 ? WEEKDAYS[new Date(`${d.date}T00:00:00`).getDay()] : fmtDate(d.date).slice(0, 5),
    date: fmtDate(d.date),
    calories: d.calories,
    recipes: d.recipes,
  }));
  const deviationStatus = r?.deviationStatus === "в норме" ? "ok" : "warn";

  return (
    <>
      <PageHeader title="Отчёты о пищевой ценности" subtitle="Выборочная выгрузка за указанный интервал.">
        <Button busy={exporting === "pdf"} onClick={() => exportAs("pdf")}>PDF</Button>
        <Button busy={exporting === "xlsx"} onClick={() => exportAs("xlsx")}>XLSX</Button>
        <Button className="primary" onClick={() => validPeriod ? setQuery(params) : notify("Некорректный период", "error")}>Сформировать</Button>
      </PageHeader>

      <Panel title="Параметры отчёта" hint="Отчёт о пищевой ценности">
        <form className="form-grid" onSubmit={(e) => { e.preventDefault(); setQuery(params); }}>
          <div className="field"><label htmlFor="date-start">Начало периода</label><input id="date-start" type="date" value={params.dateFrom} onChange={set("dateFrom")} /></div>
          <div className="field"><label htmlFor="date-end">Конец периода</label><input id="date-end" type="date" value={params.dateTo} onChange={set("dateTo")} /></div>
          <div className="field">
            <label htmlFor="format">Формат</label>
            <div className="inline" style={{ flexWrap: "nowrap" }}>
              <select id="format" value={params.format} onChange={set("format")}>
                <option value="pdf">PDF</option><option value="xlsx">XLSX</option><option value="csv">CSV</option>
              </select>
              <Button busy={exporting === params.format} onClick={() => exportAs(params.format)}>Экспорт</Button>
            </div>
          </div>
          <div className="field">
            <label htmlFor="goal">Цель</label>
            <select id="goal" value={params.goalId} onChange={set("goalId")}>
              <option value="">Все цели</option>
              {(goals.data || []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
          <button type="submit" hidden />
        </form>
      </Panel>

      {report.error && <div className="mt-18"><ErrorBox error={report.error} /></div>}
      {report.loading && !r ? <Loading /> : r && (
        <>
          <section className="layout grid-4 mt-18">
            <Metric label="Средняя калорийность" value={`${fmt(r.averageCalories)} ккал`} hint={`дней с данными: ${r.daysWithData} · рецептов в рационе: ${r.recipesCount}`} />
            <Metric label="Белки за период" value={`${fmt(r.totalProtein)} г`} />
            <Metric label="Жиры за период" value={`${fmt(r.totalFat)} г`} />
            <Metric label="Углеводы за период" value={`${fmt(r.totalCarbs)} г`} />
          </section>

          <section className="layout grid-2-wide mt-18">
            <div className="chart-card">
              <div className="panel-header" style={{ padding: "0 0 12px", borderBottom: 0 }}><h2>Калорийность по дням</h2><span>ккал</span></div>
              {r.recipesCount === 0 ? <Empty>За период нет рецептов в рационе. Добавьте рецепты в рацион на странице «Генерация» или «История».</Empty> : (
                <div className="chart-box">
                  <ResponsiveContainer>
                    <BarChart data={chart} margin={{ top: 10, right: 10, left: -6, bottom: 0 }}>
                      <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
                      <XAxis dataKey="label" stroke={CHART_COLORS.axis} fontSize={12} />
                      <YAxis stroke={CHART_COLORS.axis} fontSize={12} />
                      <Tooltip cursor={{ fill: "rgba(91,140,255,0.08)" }} labelFormatter={(_, p) => p?.[0]?.payload.date}
                               formatter={(v, _, p) => [`${fmt(v)} ккал (${p.payload.recipes} рец.)`, "Калорийность"]} />
                      {r.targetCalories && <ReferenceLine y={r.targetCalories} stroke={CHART_COLORS.fat} strokeDasharray="5 4" label={{ value: "цель", fill: CHART_COLORS.fat, fontSize: 12, position: "insideTopRight" }} />}
                      <Bar isAnimationActive={false} dataKey="calories" fill={CHART_COLORS.protein} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
            <Panel title="Макронутриентный баланс" hint="доля калорий за период">
              <MacroBars protein={r.macroPercent.protein} fat={r.macroPercent.fat} carbs={r.macroPercent.carbs} />
              <div style={{ height: 18 }} />
              <div className="table-wrap">
                <table style={{ minWidth: 360 }}>
                  <thead><tr><th>Показатель</th><th>Значение</th><th>Цель</th></tr></thead>
                  <tbody>
                    <tr><td>Средний день</td><td>{fmt(r.averageCalories)} ккал</td><td>{r.targetCalories ? `${fmt(r.targetCalories)} ккал` : "—"}</td></tr>
                    <tr>
                      <td>Отклонение</td>
                      <td>{r.deviationCalories !== null ? `${fmtSigned(r.deviationCalories)} ккал` : "—"}</td>
                      <td>{r.deviationStatus ? <StatusTag status={deviationStatus}>{r.deviationStatus}</StatusTag> : "—"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Panel>
          </section>
        </>
      )}

      <Panel className="mt-18" title="История отчётов" hint="Сохранённые записи nutrition_reports">
        {saved.loading && !saved.data ? <Loading /> : !saved.data?.length ? <Empty>Отчёты ещё не экспортировались</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Период</th><th>Формат</th><th>Дата формирования</th><th>Средняя калорийность</th><th>БЖУ за период, г</th><th>Статус</th><th>Действия</th></tr></thead>
              <tbody>
                {saved.data.map((s) => (
                  <tr key={s.reportId}>
                    <td className="nowrap">{fmtDate(s.dateFrom)} — {fmtDate(s.dateTo)}{s.goalName && <div className="small muted">{s.goalName}</div>}</td>
                    <td><span className={`tag ${FORMAT_TAG[s.format]}`}>{s.format.toUpperCase()}</span></td>
                    <td>{fmtDateTime(s.formedAt)}</td>
                    <td>{fmt(s.averageCalories)} ккал</td>
                    <td className="nowrap">{fmt(s.totalProtein)} / {fmt(s.totalFat)} / {fmt(s.totalCarbs)}</td>
                    <td>{s.fileAvailable ? <StatusTag status="ok">сохранён</StatusTag> : <StatusTag status="warn">файл удалён</StatusTag>}</td>
                    <td>
                      <button type="button" className="btn small" disabled={!s.fileAvailable}
                              onClick={() => downloadFile(`/reports/${s.reportId}/download`, `report.${s.format}`).catch((e) => notify(e.message, "error"))}>
                        Скачать
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
