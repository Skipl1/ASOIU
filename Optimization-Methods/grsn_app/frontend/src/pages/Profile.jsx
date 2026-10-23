import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Button, CHART_COLORS, Empty, ErrorBox, Loading, Message, Metric, PageHeader, Panel, useLoad, useToast } from "../components/ui.jsx";
import { fmt, fmtDate, fmtDateTime, fmtSigned, GOAL_TAG } from "../format.js";

const EMPTY = { weightKg: "", heightCm: "", age: "", gender: "", activityLevel: "", goalId: "" };

function toForm(p) {
  if (!p?.weightKg) return EMPTY;
  return {
    weightKg: String(p.weightKg), heightCm: String(p.heightCm), age: String(p.age),
    gender: p.gender, activityLevel: String(p.activityLevel), goalId: p.goal?.id || "",
  };
}

export default function Profile() {
  const notify = useToast();
  const data = useLoad(async () => {
    const [profile, goals, levels, history] = await Promise.all([
      api("/profile"), api("/goals"), api("/activity-levels"), api("/profile/parameter-history"),
    ]);
    return { profile, goals, levels, history };
  });
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [measure, setMeasure] = useState("");

  useEffect(() => {
    if (data.data) setForm(toForm(data.data.profile));
  }, [data.data?.profile]); // eslint-disable-line react-hooks/exhaustive-deps

  if (data.loading && !data.data) return <Loading />;
  if (data.error) return <ErrorBox error={data.error} />;
  const { profile, goals, levels, history } = data.data;
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const validate = () => {
    const list = [];
    const w = Number(form.weightKg.replace(",", ".")), h = Number(form.heightCm.replace(",", ".")), a = Number(form.age);
    if (!(w >= 30 && w <= 300)) list.push("Вес — от 30 до 300 кг");
    if (!(h >= 100 && h <= 250)) list.push("Рост — от 100 до 250 см");
    if (!(Number.isInteger(a) && a >= 14 && a <= 100)) list.push("Возраст — целое число от 14 до 100");
    if (!form.gender) list.push("Выберите пол");
    if (!form.activityLevel) list.push("Выберите уровень активности");
    if (!form.goalId) list.push("Выберите фитнес-ориентир");
    return list;
  };

  const save = async () => {
    const list = validate();
    setErrors(list);
    if (list.length) return;
    setBusy(true);
    try {
      const updated = await api("/profile", {
        method: "PUT",
        body: {
          weightKg: Number(form.weightKg.replace(",", ".")), heightCm: Number(form.heightCm.replace(",", ".")),
          age: Number(form.age), gender: form.gender, activityLevel: Number(form.activityLevel), goalId: form.goalId,
        },
      });
      const fresh = await api("/profile/parameter-history");
      data.setData((d) => ({ ...d, profile: updated, history: fresh }));
      notify("Профиль сохранён, целевая калорийность пересчитана");
    } catch (err) {
      setErrors([err.message]);
    } finally {
      setBusy(false);
    }
  };

  const addMeasure = async () => {
    const w = Number(measure.replace(",", "."));
    if (!(w >= 30 && w <= 300)) {
      notify("Вес — от 30 до 300 кг", "error");
      return;
    }
    try {
      await api("/profile/parameter-history", {
        method: "POST",
        body: { weightKg: w, heightCm: profile.heightCm, age: profile.age, activityLevel: profile.activityLevel },
      });
      setMeasure("");
      await data.reload();
      notify("Замер добавлен");
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const chart = [...history].reverse().map((h) => ({ date: fmtDate(h.recordedAt), weight: h.weightKg }));
  const targets = profile.dailyTargets;

  return (
    <>
      <PageHeader title="Профиль и фитнес-ориентир" subtitle="Данные используются для расчёта BMR, TDEE и целевой калорийности.">
        <Button className="primary" busy={busy} onClick={save}>Сохранить</Button>
      </PageHeader>

      {!profile.isComplete && (
        <div style={{ marginBottom: 18 }}>
          <Message kind="info" title="Заполните профиль">
            Укажите антропометрические параметры и выберите фитнес-ориентир — после этого станут доступны генерация рецептов и анализ рациона.
          </Message>
        </div>
      )}
      {errors.length > 0 && <div style={{ marginBottom: 18 }}><Message kind="error"><ul style={{ margin: 0 }}>{errors.map((e) => <li key={e}>{e}</li>)}</ul></Message></div>}

      <section className="layout grid-4">
        <Metric label="Вес" value={profile.weightKg ? `${fmt(profile.weightKg, 1)} кг` : "—"} />
        <Metric label="Рост" value={profile.heightCm ? `${fmt(profile.heightCm)} см` : "—"} />
        <Metric label="BMR" value={profile.bmr ? `${fmt(profile.bmr)} ккал` : "—"} hint={profile.tdee ? `TDEE ${fmt(profile.tdee)} ккал` : null} />
        <Metric label="Цель на день" value={profile.targetCalories ? `${fmt(profile.targetCalories)} ккал` : "—"}
                hint={targets ? `Б ${fmt(targets.protein)} · Ж ${fmt(targets.fat)} · У ${fmt(targets.carbs)} г` : null} />
      </section>

      <section className="layout grid-2-wide mt-18">
        <Panel title="Антропометрические параметры" hint="Текущая запись профиля">
          <form className="form" onSubmit={(e) => { e.preventDefault(); save(); }}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="weight">Вес, кг</label>
                <input id="weight" inputMode="decimal" placeholder="значение веса" value={form.weightKg} onChange={set("weightKg")} />
              </div>
              <div className="field">
                <label htmlFor="height">Рост, см</label>
                <input id="height" inputMode="decimal" placeholder="значение роста" value={form.heightCm} onChange={set("heightCm")} />
              </div>
              <div className="field">
                <label htmlFor="age">Возраст</label>
                <input id="age" inputMode="numeric" placeholder="возраст" value={form.age} onChange={set("age")} />
              </div>
              <div className="field">
                <label htmlFor="gender">Пол</label>
                <select id="gender" value={form.gender} onChange={set("gender")}>
                  <option value="">Выберите пол</option>
                  <option value="male">Мужской</option>
                  <option value="female">Женский</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="activity">Уровень активности</label>
              <select id="activity" value={form.activityLevel} onChange={set("activityLevel")}>
                <option value="">Выберите уровень активности</option>
                {levels.map((l) => <option key={l.value} value={String(l.value)}>{l.description} (k = {l.value})</option>)}
              </select>
            </div>
            <button type="submit" hidden />
          </form>
        </Panel>

        <Panel title="Фитнес-ориентир" hint="Коррекция целевой калорийности">
          <div className="list" role="radiogroup">
            {goals.map((g) => (
              <label className="choice-card" key={g.id}>
                <input type="radio" name="fitness-goal" checked={form.goalId === g.id} onChange={() => setForm({ ...form, goalId: g.id })} />
                <div className="choice-card-text" style={{ flex: 1 }}>
                  <strong>{g.name}</strong>
                  <span>{g.calcRule || g.description}</span>
                  <span>Б/Ж/У: {fmt(g.proteinPct)} / {fmt(g.fatPct)} / {fmt(g.carbPct)} %</span>
                </div>
                <span className={`tag ${GOAL_TAG[g.code] || "blue"}`}>{g.calorieDelta ? `${fmtSigned(g.calorieDelta)} ккал` : "Δ = 0"}</span>
              </label>
            ))}
          </div>
        </Panel>
      </section>

      <section className="layout grid-2-wide mt-18">
        <Panel title="История замеров" hint="Динамика физических параметров">
          {history.length === 0 ? <Empty>Замеров пока нет — они появятся после сохранения профиля.</Empty> : (
            <div className="table-wrap">
              <table style={{ minWidth: 480 }}>
                <thead><tr><th>Дата</th><th>Вес, кг</th><th>Рост, см</th><th>Возраст</th><th>k</th></tr></thead>
                <tbody>
                  {history.slice(0, 12).map((h) => (
                    <tr key={h.id}><td>{fmtDateTime(h.recordedAt)}</td><td>{fmt(h.weightKg, 1)}</td><td>{fmt(h.heightCm)}</td><td>{h.age}</td><td>{h.activityLevel}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {profile.weightKg && (
            <div className="inline mt-16">
              <input className="input-sm" style={{ width: 140 }} inputMode="decimal" placeholder="новый вес, кг" value={measure}
                     onChange={(e) => setMeasure(e.target.value)} aria-label="Новый замер веса" />
              <Button className="small" onClick={addMeasure}>Добавить замер</Button>
            </div>
          )}
        </Panel>
        <Panel title="Динамика веса" hint="кг">
          {chart.length < 2 ? <Empty>Для графика нужно минимум два замера.</Empty> : (
            <div className="chart-box">
              <ResponsiveContainer>
                <LineChart data={chart} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                  <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
                  <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={12} />
                  <YAxis stroke={CHART_COLORS.axis} fontSize={12} allowDecimals={false} domain={[(min) => Math.floor(min - 0.5), (max) => Math.ceil(max + 0.5)]} />
                  <Tooltip formatter={(v) => [`${fmt(v, 1)} кг`, "Вес"]} />
                  <Line isAnimationActive={false} type="monotone" dataKey="weight" stroke={CHART_COLORS.line} strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {profile.isComplete && (
            <p className="muted small" style={{ marginBottom: 0 }}>
              Далее: <Link className="btn link" to="/restrictions">укажите запреты</Link> и <Link className="btn link" to="/ingredients">выберите доступные ингредиенты</Link>.
            </p>
          )}
        </Panel>
      </section>
    </>
  );
}
