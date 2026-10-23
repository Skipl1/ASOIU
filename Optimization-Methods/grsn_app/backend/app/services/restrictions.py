"""Учёт запретов пользователя (ТЗ 4.7): нормализация, сопоставление со справочниками, проверка рецепта."""

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Allergen, Ingredient, UserRestriction

_NON_WORD = re.compile(r"[^0-9a-zа-я%.]+")
_SPACES = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Приведение регистра, замена ё, удаление лишних символов и пробелов."""
    text = value.lower().replace("ё", "е")
    text = _NON_WORD.sub(" ", text)
    return _SPACES.sub(" ", text).strip(" .")


def _stem(word: str) -> str:
    """Грубое отсечение окончаний для сопоставления словоформ («арахиса» → «арахис»)."""
    if len(word) <= 4:
        return word
    for ending in ("ами", "ями", "ого", "его", "ому", "ему", "ой", "ей", "ий", "ый", "ая", "яя", "ое", "ее",
                   "ов", "ев", "ам", "ям", "ах", "ях", "ы", "и", "а", "я", "у", "ю", "е", "о"):
        if word.endswith(ending) and len(word) - len(ending) >= 4:
            return word[: -len(ending)]
    return word


def _match_score(query: str, candidate: str) -> int:
    """0 — нет совпадения, 3 — точное, 2 — по основам слов, 1 — частичное вхождение."""
    if not query or not candidate:
        return 0
    if query == candidate:
        return 3
    q_stems = [_stem(w) for w in query.split()]
    c_stems = [_stem(w) for w in candidate.split()]
    if q_stems == c_stems:
        return 3
    if all(any(cs.startswith(qs) or qs.startswith(cs) for cs in c_stems) for qs in q_stems):
        return 2
    if len(query) >= 3 and (query in candidate or candidate in query):
        return 1
    return 0


@dataclass
class MatchCandidate:
    type: str  # ingredient | allergen
    id: uuid.UUID
    name: str
    matched_by: str
    score: int


def find_matches(db: Session, text: str, limit: int = 10) -> list[MatchCandidate]:
    query = normalize_text(text)
    if not query:
        return []
    found: list[MatchCandidate] = []

    for allergen in db.scalars(select(Allergen)):
        names = [allergen.name, *(allergen.synonyms or [])]
        best = max(((_match_score(query, normalize_text(n)), n) for n in names), default=(0, ""))
        if best[0]:
            found.append(MatchCandidate("allergen", allergen.allergen_id, allergen.name, best[1], best[0]))

    for ingredient in db.scalars(select(Ingredient)):
        names = [ingredient.name, *(ingredient.name_synonyms or [])]
        best = max(((_match_score(query, normalize_text(n)), n) for n in names), default=(0, ""))
        if best[0]:
            found.append(MatchCandidate("ingredient", ingredient.ingredient_id, ingredient.name, best[1], best[0]))

    found.sort(key=lambda m: (-m.score, m.type != "allergen", m.name))
    return found[:limit]


def resolve_unique(matches: list[MatchCandidate]) -> MatchCandidate | None:
    """Однозначное соответствие: единственный кандидат с максимальным (точным) баллом."""
    if not matches:
        return None
    top = matches[0].score
    best = [m for m in matches if m.score == top]
    if len(best) == 1 and top >= 2:
        return best[0]
    return None


@dataclass
class ForbiddenSet:
    ingredient_ids: dict[uuid.UUID, str] = field(default_factory=dict)  # id -> исходное название запрета
    allergen_ids: dict[uuid.UUID, str] = field(default_factory=dict)  # id -> название аллергена
    substances: list[str] = field(default_factory=list)  # нормализованные свободные запреты

    @property
    def is_empty(self) -> bool:
        return not (self.ingredient_ids or self.allergen_ids or self.substances)

    def describe(self) -> list[str]:
        items = [f"ингредиент «{name}»" for name in self.ingredient_ids.values()]
        items += [f"аллерген «{name}»" for name in self.allergen_ids.values()]
        items += [f"вещество «{s}»" for s in self.substances]
        return items


def load_forbidden(db: Session, user_id: uuid.UUID) -> ForbiddenSet:
    forbidden = ForbiddenSet()
    for r in db.scalars(select(UserRestriction).where(UserRestriction.user_id == user_id)):
        if r.restriction_type == "ingredient" and r.ingredient_id:
            forbidden.ingredient_ids[r.ingredient_id] = r.ingredient.name if r.ingredient else r.original_name
        elif r.restriction_type == "allergen" and r.allergen_id:
            forbidden.allergen_ids[r.allergen_id] = r.allergen.name if r.allergen else r.original_name
        else:
            forbidden.substances.append(r.normalized_name)
    return forbidden


def effective_allergens(ingredient: Ingredient, _depth: int = 0) -> list[Allergen]:
    """Аллергены ингредиента с учётом компонентов составного продукта."""
    result = {a.allergen_id: a for a in ingredient.allergens}
    if ingredient.is_composite and _depth < 5:
        for component in ingredient.components:
            for a in effective_allergens(component, _depth + 1):
                result.setdefault(a.allergen_id, a)
    return sorted(result.values(), key=lambda a: a.name)


def _substance_hit(ingredient: Ingredient, substance: str) -> bool:
    names = [ingredient.name, *(ingredient.name_synonyms or [])]
    if ingredient.composition_description:
        names.append(ingredient.composition_description)
    return any(_match_score(substance, normalize_text(n)) for n in names)


def check_ingredient(ingredient: Ingredient, forbidden: ForbiddenSet, _depth: int = 0, _parent: str | None = None) -> list[str]:
    """Правило ТЗ 4.7.2: ингредиент недопустим, если совпадает по ID с запрещённым,
    содержит запрещённый аллерген или является составным с нарушающим компонентом."""
    reasons: list[str] = []
    label = f"«{ingredient.name}»" if _parent is None else f"«{_parent}» (компонент «{ingredient.name}»)"

    if ingredient.ingredient_id in forbidden.ingredient_ids:
        reasons.append(f"{label} входит в список запрещённых ингредиентов")
    for allergen in ingredient.allergens:
        if allergen.allergen_id in forbidden.allergen_ids:
            reasons.append(f"{label} содержит запрещённый аллерген «{allergen.name}»")
    for substance in forbidden.substances:
        if _substance_hit(ingredient, substance):
            reasons.append(f"{label} совпадает с запрещённым веществом «{substance}»")

    if ingredient.is_composite and _depth < 5:
        for component in ingredient.components:
            reasons += check_ingredient(component, forbidden, _depth + 1, _parent or ingredient.name)
    return reasons


def check_ingredients(ingredients: list[Ingredient], forbidden: ForbiddenSet) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for ingredient in ingredients:
        for reason in check_ingredient(ingredient, forbidden):
            if reason not in reasons:
                reasons.append(reason)
    return not reasons, reasons


def forbidden_terms(db: Session, forbidden: ForbiddenSet) -> list[str]:
    """Названия и синонимы всего, что запрещено пользователю: ингредиенты (в том числе содержащие
    запрещённые аллергены или компоненты), сами аллергены и свободные «вещества»."""
    if forbidden.is_empty:
        return []
    terms: set[str] = set(forbidden.substances)
    safe_labels: set[str] = set()
    for ingredient in db.scalars(select(Ingredient)):
        if check_ingredient(ingredient, forbidden):
            terms.add(ingredient.name)
            terms.update(ingredient.name_synonyms or [])
        else:  # общее название («колбаса») не должно запрещаться из-за одного небезопасного продукта
            safe_labels.update(normalize_text(label) for label in (ingredient.name, *(ingredient.name_synonyms or [])))
    terms = {t for t in terms if t in forbidden.substances or normalize_text(t) not in safe_labels}
    if forbidden.allergen_ids:
        for allergen in db.scalars(select(Allergen).where(Allergen.allergen_id.in_(list(forbidden.allergen_ids)))):
            terms.add(allergen.name)
            terms.update(allergen.synonyms or [])
    result = []
    for term in terms:
        words = [w for w in normalize_text(term).split() if any(ch.isalpha() for ch in w) and len(w) >= 3]
        if words:
            result.append(" ".join(words))
    return sorted(set(result))


_ALTERNATIONS = {"г": "ж", "к": "ч", "х": "ш", "ж": "г", "ч": "к", "ш": "х"}


def _stem_variants(stem: str) -> set[str]:
    """Основа и её вариант с чередованием конечной согласной: творог/творож-ный, молок-о/молоч-ный."""
    variants = {stem}
    if len(stem) >= 4 and stem[-1] in _ALTERNATIONS:
        variants.add(stem[:-1] + _ALTERNATIONS[stem[-1]])
    return variants


def text_mentions(text: str, terms: list[str]) -> list[str]:
    """Какие из терминов упоминаются в тексте (с учётом словоформ: «творог» — «творогом», «творожный»)."""
    stems = [_stem(w) for w in normalize_text(text).split()]
    hits = []
    for term in terms:
        term_stems = [_stem_variants(_stem(w)) for w in term.split()]
        if all(any(s.startswith(v) or (len(s) >= 4 and v.startswith(s)) for s in stems for v in variants)
               for variants in term_stems):
            hits.append(term)
    return hits

