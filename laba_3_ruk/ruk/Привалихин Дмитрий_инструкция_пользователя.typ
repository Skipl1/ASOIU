#import "../../lib/lib.typ": *

// Титульный лист
#page(
  paper: "a4",
  margin: (left: 3cm, right: 1.5cm, top: 2cm, bottom: 2cm),
  numbering: none,
)[
  #set text(font: "Times New Roman", size: 14pt, lang: "ru")
  #v(8cm)
  #align(center)[
    #set par(first-line-indent: 0cm, justify: false)
    #text(weight: "bold", size: 14pt)[Инструкция для пользователей \
    автоматизированной системы генерации \
    персонализированных рецептов спортивного питания \
    (АС ГРСН)]

    #text(weight: "bold", style: "italic", size: 12pt)[(составил студент Привалихин Дмитрий, ИСИб-23-1)]
  ]
]

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
