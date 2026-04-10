#import "../../lib/lib.typ": *
#import "../../lib/resources/tz.typ": tz_title, tz_end_page


#show: tz_title.with(
  student: "Д.С. Привалихин",
  group: "ИСИб-23-1",
  teacher: "Д. С. Шипицын",
  type_as: "Разработка генеративной модели для создания персонализированных рецептов спортивного питания на основе доступных ингредиентов, целей пользователя и ограничений по аллергии",
  object: "Автоматизированная система генерации персонализированных рецептов спортивного питания",
  short_name: "АС ГРСН",
  year: "2026"
)

#show: report



// Заголовки не жирные
#show heading: it => {
  set text(weight: "regular")
  it
}

#counter(page).update(2)

#show outline.entry.where(level: 1): it => {
  v(12pt, weak: true)
  it
}

#outline(title: [Содержание])

#pagebreak()

#include "content.typ"

#pagebreak()

#tz_end_page(
  student: "Д.С. Привалихин",
  teacher: "Д. С. Шипицын",
  group: "ИСИб-23-1",
  institute: "ИРНИТУ"
)