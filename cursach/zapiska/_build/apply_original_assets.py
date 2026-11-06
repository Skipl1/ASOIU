"""Migrate the coursework from generated images to its retained project material."""
from pathlib import Path
base=Path(__file__).resolve().parent
main=base/'build_coursework.py';s=main.read_text(encoding='utf-8')
start=s.index("page('Исходный процесс')");end=s.index("page('1.2",start)
s=s[:start]+'''page('Исходный процесс')
text("""Исходный ручной процесс рассматривается как последовательность подготовки одного приёма пищи. Человек использует собственные параметры, перечень продуктов и ограничения. Результат должен содержать согласованный состав и рассчитанную пищевую ценность.""")
smalltitle('1 Определение потребности')
text("""Пользователь выбирает цель питания и определяет суточный энергетический ориентир. Для отдельного блюда устанавливается доля суточной нормы.""")
smalltitle('2 Подготовка набора продуктов')
text("""Проверяются наличие и количество продуктов, их состав и пищевая ценность. Отдельно отмечаются запреты на продукты, аллергены и вещества.""")
smalltitle('3 Поиск и проверка рецепта')
text("""Человек ищет подходящее блюдо, сопоставляет состав с наличием и проверяет ограничения. При конфликте возвращается к поиску или подбирает допустимую замену.""")
smalltitle('4 Расчёт и корректировка порции')
text("""Для выбранных масс суммируются БЖУ и энергия. После замены ингредиента расчёт повторяется. Ограниченный набор может не позволить точно достичь целевого значения.""")
smalltitle('5 Принятие и учёт решения')
text("""Пользователь выбирает пригодный вариант и записывает его для дальнейшего учёта. Просмотр предложения не означает его включения в рацион.""")
text("""Недостаток процесса заключается в разрыве между поиском, проверкой, пересчётом и учётом. Проектируемый процесс генерации, который связывает эти действия, представлен на рисунке И.3; информационные потоки показаны на рисунке И.6. Эти схемы относятся к предполагаемой автоматизированной работе и не выдаются за изображение существующего ручного процесса.""")

'''+s[end:]
s=s.replace('Контекст взаимодействия представлен на рисунке 2.','Контекст взаимодействия представлен на рисунке Е.1.')
s=s.replace("figure('c4-context','Контекст АС ГРСН',maxheight=127)\n",'')
s=s.replace("'part3.py'","'part3_original.py'")
main.write_text(s,encoding='utf-8')

file=base/'part2.py';s=file.read_text(encoding='utf-8')
s=s.replace('Разделение вариантов использования представлено на рисунке 3.','Роли и границы взаимодействия показаны на контекстной схеме Е.1; распределение экранных функций — на схеме Д.13.')
s=s.replace("figure('use-cases','Варианты использования АС ГРСН',maxheight=158)",'''text("""Для посетителя доступны регистрация и вход. После аутентификации пользователь получает доступ к собственному профилю, продуктам, ограничениям и результатам. Общие справочники и служебные действия отделены административным полномочием.

Основной пользовательский маршрут проходит через профиль, ограничения, продукты, генерацию и принятие рецепта. История, отчёты и анализ используют результаты этих действий. Административный маршрут включает поддержание общих справочников, поиск учётной записи и изменение её состояния. Прямое редактирование личного рациона другого человека не является обычной административной задачей.

Контекстная схема показывает участников и внешнюю службу генерации. Экранная структура Д.13 раскрывает доступные направления работы. Эти представления используются с их исходным назначением; контекст не обозначается как UML-диаграмма вариантов использования.""")''')
s=s.replace('Распределение ответственности компонентов показано на рисунке 4.','Распределение ответственности компонентов показано на рисунке Е.2.')
s=s.replace("figure('c4-container','Распределение компонентов АС ГРСН',maxheight=104)",'''text("""Клиентский интерфейс отвечает за ввод и отображение. Nginx выдаёт клиентское приложение и передаёт обращения к серверному API. Прикладной сервер проверяет данные, формирует контекст генерации, выполняет расчёт и сохраняет результат. PostgreSQL хранит персональные, справочные и операционные записи.

Внешняя модель предлагает варианты рецепта, но не заменяет серверную проверку. Отчёты и резервные копии относятся к отдельным хранилищам. Концепция должна обеспечивать постоянное хранение данных независимо от перезапуска прикладного компонента.""")''')
file.write_text(s,encoding='utf-8')

old=(base/'part3.py').read_text(encoding='utf-8')
nsi=old[old.index("page('3.2"):old.index("page('3.3")]
start=nsi.index("text('''Базовый макет");end=nsi.index("text('''Порядок",start)
nsi=nsi[:start]+'''text("""Доступ к НСИ предусмотрен в административном разделе, показанном на рисунке Д.12. Вкладки ингредиентов, категорий и аллергенов разделяют типы справочных записей. Последовательность работы со справочниками показана на рисунке И.5. Состав полей карточек определяется описанными выше атрибутами НСИ; отдельный новый макет карточки не вводится.""")
'''+nsi[end:]
file=base/'part3_original.py';s=file.read_text(encoding='utf-8').replace('# NSI_PRESERVED_BLOCK',nsi)
s=s.replace("['RecipeHistoryService / RatingService'","['RecipeHistoryService'")
file.write_text(s,encoding='utf-8')

file=base/'part_end.py';s=file.read_text(encoding='utf-8')
start=s.index('# The physical dictionary');end=s.index('# Group compact tables',start)
s=s[:start]+'''# Read the physical dictionary from the retained model data, without importing application code.
models=SOURCE_MODELS

'''+s[end:]
s=s.replace('Словарь раскрывает все хранимые атрибуты 17 предполагаемых прикладных таблиц.', 'Словарь раскрывает 143 поля 17 предполагаемых прикладных таблиц.')
start=s.index('# Remove superseded source citations')
appendices='''# Original illustrations are embedded byte-for-byte; no generated replacement is accepted.
for letter,title,items in ORIGINAL_GROUPS:
    for i,(asset,caption) in enumerate(items):
        image_file=ORIGINAL_IMAGES[asset]['file']
        iw,ih=Image.open(image_file).size
        landscape=iw/ih>1.25
        page('Приложение '+letter+': '+caption,appendix=True,landscape=landscape)
        if i==0:
            h('Приложение '+letter,structural=True,toc=False)
            h(title,structural=True,toc=False)
            HEADINGS.append(('Приложение '+letter+' '+title,1,PAGE,'s'+str(BOOKMARK)))
        else:
            p('Продолжение приложения '+letter,align=WD_ALIGN_PARAGRAPH.CENTER,indent=False,bold=True,after=12)
        figure(asset,caption,maxheight=(134 if i==0 else 147) if landscape else (213 if i==0 else 225),width=257 if landscape else 170,number=ORIGINAL_IMAGES[asset]['ref'])

'''
s=s[:start]+appendices+s[start:]
s=s.replace('Предметные и сервисные классы разделяют хранение данных, контроль запретов, числовой расчёт и генерацию предложения.', 'Обязанности предметных объектов и сервисов согласованы с сущностями модели данных и компонентной структурой: хранение данных отделено от контроля запретов, числового расчёта и генерации предложения.')
s=s.replace("D.save(OUT)",'''# Save to an independent temporary package first; a Word lock must not lose the edit.
import shutil
temp_output=Path(os.environ['TEMP'])/'codex-course-original-assets'/'revised.docx'
D.save(temp_output)
try:
    shutil.copyfile(temp_output,OUT)
except PermissionError:
    OUT=BASE/'Обновлённые схемы'/OUT.name
    OUT.parent.mkdir(exist_ok=True)
    shutil.copyfile(temp_output,OUT)
(BASE/'_build'/'source-assets-manifest.json').write_text(json.dumps({'output':str(OUT),'illustrations':IMAGE_MANIFEST,'schema_source':'Optimization-Methods/laba_2/diagrams/Bd','tables':17,'columns':143,'relationships':25},ensure_ascii=False,indent=2),encoding='utf-8')''')
file.write_text(s,encoding='utf-8')
print('Replaced generated illustration references; added source appendices and original schema dictionary')
