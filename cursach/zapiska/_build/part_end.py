page('Заключение');h('Заключение',structural=True)
text('''В курсовой работе выполнено предпроектное обследование деятельности специалистов по подбору рецептов спортивного питания и сформирована концепция АС ГРСН. Исходный процесс показал разрыв между поиском блюда, проверкой ограничений, расчётом пищевой ценности и учётом выбранного варианта. На этой основе определены границы автоматизации и проверяемые цели системы.

Рассмотрены пять аналогичных решений: Eat This Much, SuperCook, MyFitnessPal, Cronometer и FatSecret. Сравнение позволило принять полезные подходы к подбору по имеющимся продуктам, заданию пищевых целей, раздельному хранению рецептов и учтённого рациона, поиску и аналитике. Сделан вывод о необходимости самостоятельного согласования всей совокупности требований проекта, без утверждения отсутствия аналогов на рынке.

Для формирования требований проанализированы предметные сведения и выполнена проверка отдельных расчётных гипотез на исследовательском макете. Выделены необходимость заполнения профиля, нормализации запретов, проверки составных продуктов, объяснения недостаточного набора и отдельного принятия рецепта. Эти выводы обосновывают концепцию будущей системы; её готовность к эксплуатации и приёмка в настоящей работе не заявляются.

Разработаны ролевое представление, требования по функциям управления, технические и организационные условия. Спроектированы порядок входа и проверки полномочий, НСИ и правила её ведения, макеты основных экранов и сообщения. Логическая модель представлена на русском языке, физическая модель содержит 17 прикладных таблиц с ключами и ограничениями. Обязанности предметных объектов и сервисов согласованы с сущностями модели данных и компонентной структурой: хранение данных отделено от контроля запретов, числового расчёта и генерации предложения.

Достоинства выбранной концепции — единая цепочка проверки, прослеживаемая связь запроса и результата, независимость числового расчёта от внешней модели, а также явное разделение предложения и учтённого рациона. Сложность проектирования связана с неоднозначными наименованиями продуктов, составными ингредиентами и невозможностью точного достижения цели при любом ограниченном наборе. Поэтому отказ и фактическое отклонение являются полноправными результатами работы системы.

Дальнейшее развитие предусматривает проверку понятности интерфейса с пользователями по подготовленному интервью, расширение и уточнение источников НСИ, учёт фактической даты приёма пищи и более строгую версионность пищевых значений. Возможны интеграции с трекерами активности и внешними продуктовыми каталогами при согласовании качества и состава передаваемых данных. Принятые решения дают основу для последующего уточнения требований и развития системы; внедрение и приёмка в реальной организации в рамках работы не заявляются.''')

page('Определения, обозначения и сокращения');h('Определения, обозначения и сокращения',structural=True)
text('''В работе используются следующие определения и сокращения. Они относятся к проекту АС ГРСН и помогают различать пользовательские действия, предметные состояния и технические компоненты.''')
table('Термины и сокращения',['Термин','Значение'],[
 ['АС ГРСН','Автоматизированная система генерации персонализированных рецептов спортивного питания'],
 ['БЖУ','Белки, жиры и углеводы'],
 ['НСИ','Нормативно-справочная информация'],
 ['BMR','Расчётный базовый обмен энергии'],
 ['TDEE','Расчётная суточная потребность с учётом активности'],
 ['API','Программный интерфейс взаимодействия компонентов'],
 ['JWT','Токен, передавающий проверяемые сведения о сеансе'],
 ['PK; FK','Первичный ключ; внешний ключ'],
 ['UUID','Универсальный уникальный идентификатор'],
 ['Аутентификация','Проверка предъявленных данных входа'],
 ['Авторизация','Проверка права на конкретное действие или ресурс'],
 ['Принятый рецепт','Вариант, который пользователь отдельно включил в рацион'],
 ['Составной ингредиент','Продукт, у которого в НСИ определены компоненты'],
 ['Провайдер рецепта','Источник предложения состава и инструкции приготовления']],[44,126])

SOURCES=['Рекомендации по написанию курсовой работы (2026) ; Правила оформления КР по проектированию АСОИУ_2026 ; Правила оформления текста КР (2026). Учебно-методические материалы дисциплины «Проектирование АСОИУ». Иркутск : ИРНИТУ, 2026.', 'СТО 005–2026. Система менеджмента качества. Учебно-методическая деятельность. Оформление курсовых проектов (работ) и выпускных квалификационных работ технических специальностей. Иркутск : ИРНИТУ, 2026. 43 с.', 'Eat This Much. How to use Eat This Much // Официальная справка. URL: https://www.eatthismuch.com/how-to/ (дата обращения: 06.11.2026).', 'SuperCook Recipe By Ingredient // App Store. Карточка разработчика AMR Systems LLC. URL: https://apps.apple.com/us/app/supercook-recipe-by-ingredient/id1477747816 (дата обращения: 06.11.2026).', 'MyFitnessPal. How to create and find your recipes ; Your Today tab // Официальная справка. URL: https://support.myfitnesspal.com/hc/en-us/articles/360032271452-How-to-create-and-find-your-recipes ; https://support.myfitnesspal.com/hc/en-us/articles/39985611667341-Your-Today-tab (дата обращения: 06.11.2026).', 'Cronometer. Web Quick Start Guide ; официальный сайт. URL: https://support.cronometer.com/hc/en-us/articles/360021897491-Web-Quick-Start-Guide ; https://cronometer.com/ (дата обращения: 06.11.2026).', 'Счётчик калорий от FatSecret // Google Play. Карточка разработчика. URL: https://play.google.com/store/apps/details?id=com.fatsecret.android&hl=ru (дата обращения: 06.11.2026).', 'PostgreSQL Global Development Group. PostgreSQL 15 Documentation. 5.4 Constraints. URL: https://www.postgresql.org/docs/15/ddl-constraints.html (дата обращения: 06.11.2026).', 'FastAPI. Features // Официальная документация. URL: https://fastapi.tiangolo.com/features/ (дата обращения: 06.11.2026).', 'GigaChat API. Руководства // Документация для разработчиков. URL: https://developers.sber.ru/docs/ru/gigachat/guides/main (дата обращения: 06.11.2026).', 'Материалы предпроектной проверки расчётных гипотез АС ГРСН от 06.11.2026. Контрольные сценарии исследовательского макета. Электронный рабочий материал к настоящей работе.']
page('Список использованных источников');h('Список использованных источников',structural=True)
for i,t in enumerate(SOURCES,1):p(f'{i} {t}',indent=False,after=5)

def app(letter,title,new=True):
    page('Приложение '+letter,appendix=True)
    if new:
        h('Приложение '+letter,structural=True,toc=False)
        HEADINGS.append(('Приложение '+letter+' '+title,1,PAGE,'s'+str(BOOKMARK)))

app('А','Материалы предпроектного анализа')
table('Таблица А.1 – Состав анализируемых сведений',['Блок сведений','Какие данные необходимы','Значение для концепции'],[
 ['Параметры человека','Масса, рост, возраст, пол, уровень активности','Определить исходные величины расчётного ориентира'],
 ['Цель питания','Фитнес-ориентир и ожидаемый результат','Разделить исходную потребность и расчётные параметры'],
 ['Доступные продукты','Название, наличие, количество, состав и пищевая ценность','Ограничить набор и допустимые массы'],
 ['Пищевые ограничения','Ингредиент, аллерген или наименование','Определить порядок выявления конфликтов'],
 ['Выбор и учёт блюда','Состав, масса, решение человека, дата записи','Разделить предложение и принятый вариант']],[43,63,64],number=False)

app('А','',new=False)
table('Таблица А.2 – Примеры форм сбора предметной информации',['Форма','Поля и способ фиксации','Что нужно уточнить'],[
 ['Карточка параметров','Масса, рост, возраст, пол, активность; единицы измерения','Какие сведения человек знает и как часто обновляет'],
 ['Лист доступных продуктов','Название; количество в граммах; состояние продукта; источник пищевой ценности','Как различать сухой и готовый продукт, учитывать остаток'],
 ['Лист ограничений','Исходная формулировка; конкретный продукт или аллерген; состав','Как разрешать неоднозначное название и проверять компоненты'],
 ['Карточка ручного подбора','Исходный набор; найденный рецепт; замены; пересчёты; причины отказа','Где повторяется ввод и возникает возврат к поиску'],
 ['Лист учёта рациона','Выбранное блюдо; масса; дата; решение о включении','Как отличать просмотр варианта от принятого решения']],[40,70,60],number=False)

app('Б','Проверка предпроектных расчётных гипотез')
table('Таблица Б.1 – Ввод исходных данных и проверка ограничений',['Шаги','Действие','Наблюдаемый результат'],[
 ['1','Регистрация технической записи','201; роль user, состояние active, сеанс 1800 с'],
 ['2–3','Открытие профиля и целей','200; профиль неполный; доступно 4 цели'],
 ['4','Генерация без профиля','400; требование заполнить параметры'],
 ['5','Сохранение профиля и цели набора','200; BMR 1887,5; TDEE 2925,7; цель 3225,7 ккал'],
 ['6','Чтение каталога','200; 65 ингредиентов с пищевой ценностью'],
 ['7','Добавление запрета «Овсянка»','201; сопоставлено с овсяными хлопьями'],
 ['8','Повторное чтение каталога','200; исключены 3 позиции, включая гранолу'],
 ['9–10','Набор из одного продукта и запрос','Сохранение 200; запрос 201/status failed; 2 конфликта и 6 рекомендаций']],[17,65,88],number=False)

app('Б','',new=False)
table('Таблица Б.2 – Генерация, принятие и отчёт',['Шаги','Действие','Наблюдаемый результат'],[
 ['11','Сохранить допустимый набор','200; выбраны 4 ингредиента'],
 ['12','Сгенерировать локальный вариант','201; generated, provider=mock; 4 ингредиента, 7 шагов; запреты не обнаружены'],
 ['12','Проверить расчёт энергии','1065,5 ккал при цели 1074,2; сумма по составу также 1065,5'],
 ['13','Построить отчёт до принятия','200; 0 рецептов и 0 дней с данными'],
 ['14','Принять рецепт в рацион','200; признак включения установлен'],
 ['15–16','Прочитать историю и отчёт','1 принятый рецепт; 1065,5 ккал; Б/Ж/У 66,2/28,3/130,7 г']],[17,65,88],number=False)

app('В','Подготовленное интервью для уточнения требований')
table('Таблица В.1 – Вопросы и назначение интервью',['№','Вопрос','Уточняемое требование'],[
 ['1','Какие действия вы выполняете при выборе одного блюда?','Границы и последовательность процесса'],
 ['2','Какие параметры питания вы готовы указывать в профиле?','Ф2; обязательные поля'],
 ['3','Как вы понимаете выбранную цель и долю суточной нормы?','Ф5; подписи и подсказки'],
 ['4','Как вы определяете доступные продукты и их количество?','Ф3; ввод запаса'],
 ['5','Каким способом вам удобнее задавать запрет на продукт?','Ф4; поиск и нормализация'],
 ['6','Какое объяснение конфликта состава будет понятным?','Ф7; сообщение об отказе'],
 ['7','Какие сведения нужны для выбора одного из вариантов?','Ф6; карточка результата'],
 ['8','Как вы различаете просмотр рецепта и его учёт в рационе?','Ф8; действие принятия'],
 ['9','Какие фильтры нужны для поиска старого рецепта?','Ф8; история'],
 ['10','За какой период и в каком формате нужен отчёт?','Ф10; выгрузка'],
 ['11','Как вы понимаете среднее значение по дням с записями?','Ф9; пояснение полноты учёта'],
 ['12','Как проверять источник и корректность новой записи НСИ?','Ф11; контроль справочника']],[10,110,50],number=False,size=11)

# Read the physical dictionary from the retained model data, without importing application code.
models=SOURCE_MODELS

# Group compact tables by estimated line count; the renderer verifies the resulting pages.
app('Г','Полный физический словарь данных')
dictionary_groups=[
    {'users','fitness_goals'},
    {'user_profiles','parameter_history','ingredient_categories'},
    {'allergens','ingredient_allergens','ingredient_components','ingredients'},
    {'available_ingredients','user_restrictions','generation_requests'},
    {'recipes','recipe_ingredients'},
    {'recipe_ratings','nutrition_reports','audit_log'},
]
previous_group=0
for idx,(name,cols) in enumerate(models,1):
    current_group=next(i for i,g in enumerate(dictionary_groups) if name in g)
    if current_group!=previous_group:
        app('Г','',new=False);previous_group=current_group
    table(f'Таблица Г.{idx} – {name}',['Атрибут','Тип PostgreSQL','NULL','Ключ или связь'],cols,[57,35,14,64],number=False,size=10)

# Original illustrations are embedded byte-for-byte; no generated replacement is accepted.
for letter,title,items in ORIGINAL_GROUPS:
    for i,(asset,caption) in enumerate(items):
        image_file=ORIGINAL_IMAGES[asset]['file']
        iw,ih=Image.open(image_file).size
        landscape=iw/ih>1.25
        page('Приложение '+letter+': '+caption,appendix=True,landscape=landscape)
        if i==0:
            h('Приложение '+letter,structural=True,toc=False)
            HEADINGS.append(('Приложение '+letter+' '+title,1,PAGE,'s'+str(BOOKMARK)))
        figure(asset,caption,maxheight=147 if landscape else 225,width=257 if landscape else 170,number=ORIGINAL_IMAGES[asset]['ref'])

# Remove superseded source citations and renumber the remaining references.
def remap_citation(match):
    values=[]
    raw=match.group(1)
    for part in re.split(r'[;,]',raw):
        part=part.strip()
        if not part:continue
        if '–' in part or '-' in part:
            ends=re.split('[–-]',part)
            numbers=range(int(ends[0]),int(ends[1])+1)
        else:numbers=[int(part)]
        values.extend(n-4 for n in numbers if n>=5)
    if not values:return ''
    return '['+'; '.join(str(n) for n in values)+']'
for node in D.element.iter(qn('w:t')):
    if node.text:
        node.text=re.sub(r'\[([0-9][0-9; ,–-]*)\]',remap_citation,node.text)
        node.text=re.sub(r' +([.,;])',r'\1',node.text)

# Hidden native TC entries ensure an update preserves the intended outline,
# including one combined entry for each appendix rather than its two display lines.
for title,level,pg,bm in HEADINGS:
    target=D.element.xpath('.//w:bookmarkStart[@w:name="'+bm+'"]')[0].getparent()
    for kind,value in [('begin',None),('instruction',f' TC "{title}" \\f C \\l "{level}" '),('separate',None),('end',None)]:
        rr=OxmlElement('w:r');rp=OxmlElement('w:rPr');rp.append(OxmlElement('w:vanish'));rr.append(rp)
        if kind=='instruction':
            node=OxmlElement('w:instrText');node.set(qn('xml:space'),'preserve');node.text=value
        else:
            node=OxmlElement('w:fldChar');node.set(qn('w:fldCharType'),kind)
        rr.append(node);target.append(rr)

# A populated native TOC field with hyperlinks/bookmarks; cached page numbers match explicit pages.
par=TOC_PLACEHOLDER._p
idx=par.getparent().index(par);parent=par.getparent();parent.remove(par)
tocparas=[]
for title,level,pg,bm in HEADINGS:
    x=D.add_paragraph();x.paragraph_format.first_line_indent=0;x.paragraph_format.left_indent=Mm(6 if level==2 else 0)
    x.paragraph_format.line_spacing=1;x.paragraph_format.space_after=Pt(0);x.paragraph_format.space_before=Pt(0)
    x.paragraph_format.tab_stops.add_tab_stop(Mm(170),__import__('docx').enum.text.WD_TAB_ALIGNMENT.RIGHT,__import__('docx').enum.text.WD_TAB_LEADER.DOTS)
    setfont(x.add_run(title+'\t'))
    field(x,'PAGEREF '+bm+' \\h',str(pg))
    parent.remove(x._p);parent.insert(idx,x._p);idx+=1;tocparas.append(x._p)
if tocparas:
    begin=OxmlElement('w:r');fc=OxmlElement('w:fldChar');fc.set(qn('w:fldCharType'),'begin');begin.append(fc)
    instr=OxmlElement('w:r');it=OxmlElement('w:instrText');it.set(qn('xml:space'),'preserve');it.text=' TOC \\f C \\h \\z ';instr.append(it)
    sep=OxmlElement('w:r');sc=OxmlElement('w:fldChar');sc.set(qn('w:fldCharType'),'separate');sep.append(sc)
    tocparas[0].insert(0,sep);tocparas[0].insert(0,instr);tocparas[0].insert(0,begin)
    end=OxmlElement('w:r');ec=OxmlElement('w:fldChar');ec.set(qn('w:fldCharType'),'end');end.append(ec);tocparas[-1].append(end)

D.core_properties.title=TOPIC
D.core_properties.subject='Курсовая работа по дисциплине «Проектирование АСОИУ»'
D.core_properties.author='Привалихин Д. С.'
D.core_properties.keywords='АС ГРСН; предпроектное обследование; проектирование АСОИУ'
D.core_properties.comments='Подготовлено на основе материалов проекта и требований оформления 2026 года.'
# Save to an independent temporary package first; a Word lock must not lose the edit.
import shutil
temp_output=Path(os.environ['TEMP'])/'codex-course-original-assets'/'revised.docx'
D.save(temp_output)
try:
    shutil.copyfile(temp_output,OUT)
except PermissionError:
    OUT=BASE/'Обновлённые схемы'/OUT.name
    OUT.parent.mkdir(exist_ok=True)
    shutil.copyfile(temp_output,OUT)
(BASE/'_build'/'source-assets-manifest.json').write_text(json.dumps({'output':str(OUT),'illustrations':IMAGE_MANIFEST,'schema_source':'Optimization-Methods/laba_2/diagrams/Bd','tables':17,'columns':143,'relationships':25},ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'_build'/'page-plan.json').write_text(json.dumps({'pages':PAGES,'headings':HEADINGS,'figures':FIG,'tables':TABLE,'models':len(models)},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(OUT),'planned_pages':PAGE,'figures':FIG,'tables':TABLE,'dictionary_tables':len(models),'headings':len(HEADINGS)},ensure_ascii=False))
