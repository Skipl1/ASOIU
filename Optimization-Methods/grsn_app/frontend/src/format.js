export const fmt = (value, digits = 0) =>
  value === null || value === undefined || Number.isNaN(value)
    ? "—"
    : Number(value).toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const fmtSigned = (value, digits = 0) => (value > 0 ? "+" : "") + fmt(value, digits);

export const fmtDate = (value) => (value ? new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString("ru-RU") : "—");

export const fmtDateTime = (value) =>
  value ? new Date(value).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

export const isoDate = (date) => {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDate(d);
};

export const DIFFICULTY = { low: "Низкая", medium: "Средняя", high: "Высокая" };
export const PRIORITY = { high: ["red", "высокий приоритет"], medium: ["amber", "средний приоритет"], low: ["blue", "низкий приоритет"] };
export const SOURCE = { gigachat: "GigaChat", mock: "локальный генератор" };

export const MEAL_SHARES = [
  { value: 0.333, label: "1/3 нормы — 3 приёма пищи в день" },
  { value: 0.25, label: "25 % — завтрак / 4 приёма пищи" },
  { value: 0.35, label: "35 % — обед" },
  { value: 0.3, label: "30 % — ужин" },
  { value: 0.2, label: "20 % — 5 приёмов пищи" },
  { value: 0.15, label: "15 % — большой перекус" },
  { value: 0.1, label: "10 % — перекус" },
  { value: 0.4, label: "40 % — основной приём пищи" },
  { value: 0.5, label: "1/2 нормы" },
  { value: 1, label: "Вся суточная норма" },
];

// Приём пищи: подпись и доля суточной нормы по умолчанию
export const MEAL_TYPES = [
  { value: "breakfast", label: "Завтрак", share: 0.25 },
  { value: "lunch", label: "Обед", share: 0.35 },
  { value: "dinner", label: "Ужин", share: 0.3 },
  { value: "snack", label: "Перекус", share: 0.1 },
];
export const MEAL_LABEL = Object.fromEntries(MEAL_TYPES.map((m) => [m.value, m.label.toLowerCase()]));

export const GOAL_TAG = { goal_loss: "amber", goal_maintain: "blue", goal_gain: "green", goal_endurance: "teal" };

export const pluralRecipes = (n) => {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "рецепт";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "рецепта";
  return "рецептов";
};
