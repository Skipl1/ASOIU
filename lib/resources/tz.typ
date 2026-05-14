#let tz_title(
  institute: "ИРНИТУ, институт ИТиАД",
  type_as: "Разработка мультиагентной системы ситуативного обучения с динамическим синтезом и верификацией адаптивных образовательных сценариев",
  object: "Автономная цифровая среда интеллектуального тренинга",
  short_name: "МАССО",
  group: "ИСИб-23-1",
  student: "Л.А. Демонов",
  teacher: "Р.Д. Гутгарц",
  year: "2026",
  body
) = {
  set page(margin: (left: 3cm, right: 1.5cm, top: 2cm, bottom: 2cm))
  set text(font: "Times New Roman", size: 12pt, lang: "ru")


  // В коде вызываем функции БЕЗ решетки
  let fill_line(name) = grid(
    columns: (1fr, auto),
    column-gutter: 5pt,
    repeat[\_],
    name
  )

  let sign_block(title, role, name) = [
    #align(center)[#title]
    #v(0.28em)
    #align(center)[#role]
    #v(0.28em)
    #fill_line(name)
    #v(0.28em)
    #fill_line([#year г.])
    #v(0.28em)
    #align(center)[Печать]
  ]

  grid(
    columns: (1fr, 1fr),
    column-gutter: 2cm,
    sign_block("УТВЕРЖДАЮ", "Руководитель по предмету «АСОИиУ»", teacher),
    sign_block("УТВЕРЖДАЮ", "студент гр. " + group + " ИРНИТУ", student)
  )

  v(2cm)

  let central_field(content, desc) = [
    #align(center)[#content]
    #v(-1em)
    #repeat[\_]
    #v(-0.8em)
    #align(center)[#text(size: 7pt)[#desc]]
    #v(0.28em)
  ]

  central_field(institute, "наименование организации – разработчика ТЗ на АС")
  central_field(type_as, "Наименование вида АС")
  central_field(object, "наименование объекта автоматизации")
  central_field(short_name, "сокращенное наименование АС")

  v(1cm)

  align(center)[
    #text(size: 14pt, weight: "bold")[ТЕХНИЧЕСКОЕ ЗАДАНИЕ] \
    #v(0.28em)
    На \_\_\_листах \
    #v(0.28em)
    Действует с «\_\_\_\_\_\_» \_\_\_\_\_\_\_\_\_\_\_\_ #year г.
  ]

  let sign_block(title, role, name) = [
    #align(center)[#title]
    #v(0.28em)
    #align(center)[#role]
    #v(0.28em)
    
    // Линия подписи (адаптивная)
    #grid(
      columns: (1fr, auto),
      column-gutter: 5pt,
      repeat[\_],
      name
    )
    
    #v(0.5em)
    
    // Адаптивная линия даты
    #grid(
      columns: (1fr, auto),
      column-gutter: 0pt,
      [« \_\_\_ » #repeat[\_]], // Линия месяца растягивается до конца
      [ #year г.]
    )
    
    #v(1em)
    #align(center)[Печать]
  ]

  // --- БЛОК СОГЛАСОВАНО ---
  v(2cm)
  block(width: 200pt)[
    СОГЛАСОВАНО \
    #v(0.1cm)
    Руководитель \
    #v(0.1cm)
    
    // Линия подписи (адаптивная под ширину блока)
    #grid(
      columns: (1fr, auto),
      column-gutter: 5pt,
      repeat[\_],
      teacher
    )
    
    #v(0.1cm)
    
    // Линия даты (адаптивная - край совпадет с фамилией выше)
    // Линия даты (адаптивная и в одну строку)
    #grid(
      columns: (1fr, auto),
      column-gutter: 0pt,
      // Stack теперь содержит фиксированные кавычки и резиновый бокс для линии
      stack(
        dir: ltr, 
        [« \_\_\_ » ], 
        box(width: 75%, repeat[\_])
      ), 
      [ #year г.]
    )
    
    
    #v(0.1cm)
    Печать
  ]

  pagebreak()
  body
}

#let tz_end_page(
  student: "Смирнягин Руслан Владиславович",
  teacher: "Гутгарц Римма Давыдовна",
  group: "ИСИб-23-1",
  institute: "ИРНИТУ"
) = {
  set text(font: "Times New Roman", size: 12pt, lang: "ru") // В таблицах обычно шрифт чуть меньше
  
  let table_header = (
    [Наименование организации, предприятия],
    [Должность исполнителя],
    [Фамилия, имя, отчество],
    [Подпись],
    [Дата]
  )
}