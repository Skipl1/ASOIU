import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Button, Empty, ErrorBox, Loading, Message, PageHeader, Panel, StatusTag, useLoad, useToast } from "../components/ui.jsx";

const TYPE_LABEL = { allergen: "Аллерген", ingredient: "Ингредиент", substance: "Вещество" };

export default function Restrictions() {
  const notify = useToast();
  const list = useLoad(() => api("/restrictions"));
  const check = useLoad(() => api("/restrictions/check-available"));
  const [text, setText] = useState("");
  const [match, setMatch] = useState(null);
  const [choice, setChoice] = useState("");
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // Нормализация ввода и поиск соответствий в справочниках (с задержкой)
  useEffect(() => {
    const q = text.trim();
    if (q.length < 2) {
      setMatch(null);
      setChoice("");
      return undefined;
    }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const result = await api("/restrictions/match", { params: { q } });
        setMatch(result);
        const best = result.unique || result.candidates[0];
        setChoice(best ? `${best.type}:${best.id}` : "substance");
      } catch (err) {
        setError(err);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [text]);

  const refresh = () => Promise.all([list.reload(), check.reload()]);

  const add = async (e) => {
    e?.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    const [type, id] = choice.split(":");
    const body = { sourceText: text.trim() };
    if (type === "ingredient") body.ingredientId = id;
    else if (type === "allergen") body.allergenId = id;
    else body.asSubstance = true;
    try {
      await api("/restrictions", { method: "POST", body });
      setText("");
      await refresh();
      notify("Запрет добавлен в список");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (r) => {
    try {
      await api(`/restrictions/${r.id}`, { method: "DELETE" });
      await refresh();
      notify(`Запрет «${r.sourceText}» удалён`);
    } catch (err) {
      notify(err.message, "error");
    }
  };

  const clearAll = async () => {
    if (!window.confirm("Удалить все запреты пользователя?")) return;
    await api("/restrictions", { method: "DELETE" });
    await refresh();
    notify("Список запретов очищен");
  };

  const candidates = match?.candidates || [];
  const excluded = (check.data || []).filter((c) => c.result === "excluded").length;

  return (
    <>
      <PageHeader title="Аллергены и запрещённые продукты" subtitle="Единый список ограничений пользователя.">
        <Button onClick={clearAll} disabled={!list.data?.length}>Очистить</Button>
        <Button className="primary" onClick={refresh}>Проверить набор</Button>
      </PageHeader>

      <section className="split">
        <Panel title="Добавление запрета" hint="Нормализация по справочникам">
          <form className="form" onSubmit={add}>
            <div className="field">
              <label htmlFor="restriction">Продукт или вещество</label>
              <input id="restriction" placeholder="название продукта или вещества, например «молоко» или «орехи»"
                     value={text} onChange={(e) => setText(e.target.value)} autoComplete="off" />
              {match && <span className="field-hint">Нормализовано: «{match.normalized}»{searching ? " · поиск…" : ""}</span>}
            </div>
            <div className="field">
              <label htmlFor="match">Найденное соответствие</label>
              <select id="match" value={choice} onChange={(e) => setChoice(e.target.value)} disabled={!match}>
                {!match && <option value="">Введите название для поиска</option>}
                {candidates.map((c) => (
                  <option key={c.id} value={`${c.type}:${c.id}`}>
                    {TYPE_LABEL[c.type]}: {c.name}{c.exact ? "" : ` (по «${c.matchedBy}»)`}
                  </option>
                ))}
                {match && <option value="substance">Нет в справочниках — запретить по названию «{text.trim()}»</option>}
              </select>
              {match && candidates.length > 1 && !match.unique && (
                <span className="field-hint">Однозначного соответствия нет — выберите вариант из справочника.</span>
              )}
            </div>
            <ErrorBox error={error} />
            <Button type="submit" className="primary" busy={busy} disabled={!match || !choice}>Добавить в список</Button>
          </form>
        </Panel>

        <Panel title="Текущие ограничения" hint="список пользователя">
          {list.loading && !list.data ? <Loading /> : list.data?.length === 0 ? (
            <Empty>Запретов нет. Добавьте аллергены и продукты, которые нельзя использовать в рецептах.</Empty>
          ) : (
            <div className="list">
              {(list.data || []).map((r) => (
                <div className="row-item" key={r.id}>
                  <div className="row-main">
                    <strong>{r.sourceText}</strong>
                    <span>{TYPE_LABEL[r.type]}{r.targetName && r.targetName !== r.sourceText ? ` · ${r.targetName}` : ""}</span>
                  </div>
                  <div className="inline">
                    <span className="tag red">запрещён</span>
                    <button type="button" className="btn small" onClick={() => remove(r)} aria-label={`Удалить запрет ${r.sourceText}`}>Удалить</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </section>

      <Panel className="mt-18" title="Проверка выбранного набора ингредиентов"
             hint={check.data?.length ? `Результат перед генерацией · исключено: ${excluded}` : "Результат перед генерацией"}>
        {check.loading && !check.data ? <Loading /> : check.data?.length === 0 ? (
          <Empty>Набор доступных ингредиентов пуст. <Link className="btn link" to="/ingredients">Выбрать ингредиенты</Link></Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Ингредиент</th><th>Связанные аллергены</th><th>Результат</th><th>Причина</th></tr></thead>
              <tbody>
                {(check.data || []).map((c) => (
                  <tr key={c.ingredientId}>
                    <td>{c.name}</td>
                    <td>{c.allergens.length ? c.allergens.join(", ") : "—"}</td>
                    <td>{c.result === "allowed" ? <StatusTag status="ok">допустим</StatusTag> : <StatusTag status="bad">исключён</StatusTag>}</td>
                    <td>{c.reasons.length ? c.reasons.join("; ") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {excluded > 0 && (
          <div className="mt-16"><Message kind="warn">Исключённые ингредиенты не будут переданы модели генерации. Замените их в разделе «Ингредиенты».</Message></div>
        )}
      </Panel>
    </>
  );
}
