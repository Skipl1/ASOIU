#import "../../lib/lib.typ": *

// Настройка формата нумерации
#set figure(numbering: "1")

// Центрирование заголовков
#show heading: set align(center)

// Изменение префикса подписей на "Рисунок"
#set figure( supplement: [Рисунок])

// Настройка отступов для маркированных списков
#show list: set block(spacing: 5pt)
#set list(body-indent: 5pt, indent: 2.6em)
