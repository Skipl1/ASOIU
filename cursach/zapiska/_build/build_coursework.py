"""Build the coursework as native, editable Word OOXML. No Typst is used."""
from pathlib import Path
import json, sys, os, re, ast
sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_materials import source_catalog,schema_from_source
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
from PIL import Image
from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[1]
OUT=BASE/'КП_Привалихин_Черновик (07.11.2026).docx'
ASSETS=BASE/'assets'
TOPIC='Предпроектное обследование объекта автоматизации и основные проектные решения для интеллектуальной системы генерации персонализированных рецептов спортивного питания'
D=Document()
PAGE=0; FIG=0; TABLE=0; BOOKMARK=0
HEADINGS=[]; PAGES=[]; APP=None
ORIGINAL_GROUPS,ORIGINAL_IMAGES=source_catalog(REPO)
SOURCE_SCHEMA,SOURCE_MODELS,SOURCE_MODEL_GROUPS=schema_from_source(REPO)
IMAGE_MANIFEST=[]
RESTORED_IMAGES={name:ASSETS/(name+'.drawio.png') for name in ('as-is','use-cases')}

def setfont(run,size=14,bold=None):
    run.font.name='Times New Roman';run.font.size=Pt(size)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Times New Roman')
    if bold is not None:run.bold=bold
    return run

for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption','TOC Heading']:
    s=D.styles[name];s.font.name='Times New Roman';s.font.size=Pt(14);s.font.color.rgb=__import__('docx').shared.RGBColor(0,0,0)
    s.paragraph_format.line_spacing=1;s.paragraph_format.space_after=Pt(0);s.paragraph_format.space_before=Pt(0)
    s.paragraph_format.first_line_indent=Mm(12.5)
    s._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Times New Roman')
    lang=OxmlElement('w:lang');lang.set(qn('w:val'),'ru-RU');s._element.get_or_add_rPr().append(lang)
normal=D.styles['Normal'];normal.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
for style in D.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
settings=D.settings.element
auto=OxmlElement('w:doNotHyphenateCaps');settings.append(auto)
hy=OxmlElement('w:autoHyphenation');hy.set(qn('w:val'),'0');settings.append(hy)
update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)

def field(p,code,cached=''):
    r=p.add_run();b=OxmlElement('w:fldChar');b.set(qn('w:fldCharType'),'begin');r._r.append(b)
    ins=OxmlElement('w:instrText');ins.set(qn('xml:space'),'preserve');ins.text=' '+code+' ';r._r.append(ins)
    sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    setfont(p.add_run(cached))
    rr=p.add_run();e=OxmlElement('w:fldChar');e.set(qn('w:fldCharType'),'end');rr._r.append(e)

def page(label='',appendix=False,landscape=False):
    global PAGE
    PAGE+=1;PAGES.append({'page':PAGE,'label':label,'appendix':appendix,'landscape':landscape})
    s=D.sections[0] if PAGE==1 else D.add_section(WD_SECTION_START.NEW_PAGE)
    if PAGE in [2,3]:
        # The copied form already has its complete paragraph rhythm. Avoid an
        # extra normal-sized section-break line after the city/signature table.
        break_p=D.element.body[-2]
        previous=break_p.getprevious()
        if previous is not None and previous.tag==qn('w:p'):
            sect=break_p.find(qn('w:pPr')).find(qn('w:sectPr'))
            props=previous.find(qn('w:pPr'))
            if props is None:props=OxmlElement('w:pPr');previous.insert(0,props)
            props.append(sect);D.element.body.remove(break_p)
        else:
            props=break_p.find(qn('w:pPr'))
            spacing=OxmlElement('w:spacing')
            for k,v in [('before','0'),('after','0'),('line','20'),('lineRule','exact')]:spacing.set(qn('w:'+k),v)
            props.insert(0,spacing)
            rp=OxmlElement('w:rPr');sz=OxmlElement('w:sz');sz.set(qn('w:val'),'2');rp.append(sz)
            props.insert(list(props).index(props.find(qn('w:sectPr'))),rp)
    s.page_width=Mm(297 if landscape else 210);s.page_height=Mm(210 if landscape else 297)
    from docx.enum.section import WD_ORIENT
    s.orientation=WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    s.top_margin=Mm(15);s.bottom_margin=Mm(20);s.header_distance=Mm(7);s.footer_distance=Mm(10)
    # Explicit per-page sections preserve mirrored main text and one-sided appendices.
    left=30 if appendix or PAGE%2 else 10
    s.left_margin=Mm(left);s.right_margin=Mm(40-left)
    s.different_first_page_header_footer=(PAGE==1)
    s.footer.is_linked_to_previous=False
    fp=s.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER;fp.paragraph_format.first_line_indent=0
    if PAGE>1:field(fp,'PAGE',str(PAGE))
    return s

def p(text='',size=14,bold=False,align=None,indent=True,after=0,before=0,keep=False):
    x=D.add_paragraph();x.paragraph_format.first_line_indent=Mm(12.5) if indent else 0
    x.paragraph_format.line_spacing=1;x.paragraph_format.space_after=Pt(after);x.paragraph_format.space_before=Pt(before)
    x.paragraph_format.widow_control=True;x.paragraph_format.keep_with_next=keep
    x.alignment=align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    setfont(x.add_run(text),size,bold);return x

def text(t):
    for a in t.strip().split('\n\n'):p(a.replace('\n',' '))

def h(title,level=1,structural=False,toc=True):
    global BOOKMARK
    x=p(title,bold=True,align=WD_ALIGN_PARAGRAPH.CENTER if structural else WD_ALIGN_PARAGRAPH.JUSTIFY,indent=not structural,after=12,before=0,keep=True)
    x.style=D.styles['Heading '+str(level)]
    x.alignment=WD_ALIGN_PARAGRAPH.CENTER if structural else WD_ALIGN_PARAGRAPH.JUSTIFY
    x.paragraph_format.first_line_indent=0 if structural else Mm(12.5)
    x.paragraph_format.space_after=Pt(12);x.paragraph_format.keep_with_next=True
    BOOKMARK+=1;name='s'+str(BOOKMARK)
    start=OxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(BOOKMARK));start.set(qn('w:name'),name)
    end=OxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(BOOKMARK))
    x._p.insert(0,start);x._p.append(end)
    if toc:HEADINGS.append((title,level,PAGE,name))
    return x

def table(title,headers,rows,widths=None,size=12,number=True):
    global TABLE
    if number:TABLE+=1;caption=f'Таблица {TABLE} – {title}'
    else:caption=title
    p(caption,indent=False,after=5,keep=True)
    t=D.add_table(rows=1,cols=len(headers));t.autofit=False
    if widths is None:widths=[170/len(headers)]*len(headers)
    for c,w in zip(t.columns,widths):c.width=Mm(w)
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+edge);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'000000');borders.append(b)
    t._tbl.tblPr.append(borders)
    for i,row in enumerate([headers]+rows):
        cells=t.rows[0].cells if i==0 else t.add_row().cells
        for j,(c,value,w) in enumerate(zip(cells,row,widths)):
            c.width=Mm(w);pr=c._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for e in ['top','bottom','left','right']:
                q=OxmlElement('w:'+e);q.set(qn('w:w'),'65');q.set(qn('w:type'),'dxa');m.append(q)
            pr.append(m)
            cp=c.paragraphs[0];cp.paragraph_format.first_line_indent=0;cp.paragraph_format.line_spacing=1;cp.paragraph_format.space_after=Pt(0);cp.paragraph_format.space_before=Pt(0)
            cp.alignment=WD_ALIGN_PARAGRAPH.LEFT
            setfont(cp.add_run(str(value)),size,i==0)
        trpr=t.rows[i]._tr.get_or_add_trPr();nosplit=OxmlElement('w:cantSplit');trpr.append(nosplit)
        if i==0:trpr.append(OxmlElement('w:tblHeader'))
    p('',size=3,indent=False,after=0)
    return TABLE

def figure(asset,title,maxheight=150,width=170,number=None):
    global FIG
    assert asset in ORIGINAL_IMAGES or asset in RESTORED_IMAGES,('Unapproved illustration',asset)
    FIG+=1;num=number if number is not None else str(FIG)
    f=ORIGINAL_IMAGES[asset]['file'] if asset in ORIGINAL_IMAGES else RESTORED_IMAGES[asset]
    im=Image.open(f);iw,ih=im.size
    width=min(width,maxheight*iw/ih)
    x=p('',indent=False,align=WD_ALIGN_PARAGRAPH.CENTER,keep=True)
    x.add_run().add_picture(str(f),width=Mm(width))
    x.paragraph_format.line_spacing=1
    p(f'Рисунок {num} – {title}',indent=False,align=WD_ALIGN_PARAGRAPH.CENTER,after=10)
    import hashlib
    IMAGE_MANIFEST.append({'ref':num,'asset':asset,'caption':title,'source':str(f.relative_to(REPO)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'page':PAGE,'kind':'original' if asset in ORIGINAL_IMAGES else 'restored_authorized'})
    return num

def equation(expr,n):
    x=p('',indent=False,before=12,after=12)
    tabs=x.paragraph_format.tab_stops
    from docx.enum.text import WD_TAB_ALIGNMENT
    tabs.add_tab_stop(Mm(85),WD_TAB_ALIGNMENT.CENTER);tabs.add_tab_stop(Mm(170),WD_TAB_ALIGNMENT.RIGHT)
    x.add_run('\t');math=OxmlElement('m:oMath');r=OxmlElement('m:r');tt=OxmlElement('m:t');tt.text=expr;r.append(tt);math.append(r);x._p.append(math)
    setfont(x.add_run('\t('+str(n)+')'))

def define(lines):
    for i,t in enumerate(lines):p(('где ' if i==0 else '')+t,indent=(i==0))

def smalltitle(title):p(title,bold=True,indent=False,before=7,after=5,keep=True)

# Native forms are cloned from the specified course reference.
exec(compile(Path(__file__).with_name('front_matter.py').read_text(encoding='utf-8'),'front_matter.py','exec'),globals())

page('Содержание');h('Содержание',structural=True,toc=False)
TOC_PLACEHOLDER=p('TOC_PLACEHOLDER',indent=False)

page('Введение');h('Введение',structural=True)
text('''Персональный подбор спортивного питания требует согласования нескольких условий: энергетической потребности человека, целевых долей белков, жиров и углеводов, доступных продуктов и пищевых ограничений. При раздельном использовании поисковых сервисов, калькулятора и записей о рационе пользователь повторно переносит одни и те же данные. После замены ингредиента приходится заново рассчитывать состав блюда и проверять ограничения. Поэтому актуальна система, которая объединяет эти действия и сохраняет основания расчёта.

Объект автоматизации — деятельность специалистов по спортивному питанию (нутрициологов, фитнес-тренеров) по подбору индивидуальных рецептов для спортсменов и фитнес-пользователей с учётом их целей, доступных продуктов и ограничений по аллергии. Предмет автоматизации — сбор и хранение исходных данных, генерация рецептов, проверка ограничений и расчёт пищевой ценности. Система предназначена для специалистов и конечных пользователей, самостоятельно подбирающих спортивное питание.

Цель курсовой работы — выполнить предпроектное обследование и обосновать основные проектные решения интеллектуальной системы генерации персонализированных рецептов спортивного питания (АС ГРСН). Для достижения цели необходимо описать исходный процесс, сопоставить аналогичные решения, сформулировать проверяемые требования, спроектировать роли, НСИ, интерфейс, базу данных и классы.

Работа относится к предпроектному этапу: исследуются предметная область и существующий ручной процесс, выявляются потребности пользователя и обосновывается концепция будущей системы. Требования к структуре и оформлению приняты по материалам дисциплины и СТО 005–2026 [5; 6]. Для проверки отдельных расчётных гипотез используется исследовательский макет; его результаты не означают готовность проектируемой системы к эксплуатации.

Проект предусматривает веб-интерфейс, сервер прикладных правил и реляционную базу данных. Внешний генератор GigaChat предлагает содержание рецепта, а сервер проверяет ограничения и пересчитывает пищевую ценность. При недоступности внешней службы предусмотрен локальный вариант генерации. Выбор этих средств обосновывается требованиями к персонализации, воспроизводимости расчёта и разделению ответственности.

Работа выполнена Привалихиным Д. С., студентом группы ИСИб-23-1. Отдельный внешний заказчик для учебного проекта не определён; проект рассматривается как учебная разработка для конечного пользователя. Ожидаемая выгода — сокращение повторного ввода и ручного пересчёта при сохранении истории решений. Система предоставляет расчётную поддержку питания и не подменяет медицинскую оценку пищевой безопасности.''')

page('1 Характеристика объекта автоматизации')
h('1 Характеристика объекта автоматизации')
h('1.1 Описание деятельности объекта автоматизации',2)
text('''Обследуется подбор индивидуальных рецептов спортивного питания нутрициологами и фитнес-тренерами для спортсменов и фитнес-пользователей. Самостоятельный подбор конечным пользователем также входит в назначение системы. В прикладной модели сохраняются две роли: пользователь и администратор. Параметры пользователя включают массу, рост, возраст, пол, активность и фитнес-ориентир. Для подбора нужны доступные продукты, их количество и ограничения на ингредиенты, аллергены или наименования [1; 2].

В исходном процессе специалист определяет потребность человека и долю одного приёма пищи, ищет рецепт и сопоставляет состав с наличием продуктов. Затем он заменяет неподходящие позиции, рассчитывает массы ингредиентов и пищевую ценность. При обнаружении запрещённого компонента поиск повторяется. Результат фиксируется в записях о рационе. При самостоятельном подборе эти действия выполняет сам конечный пользователь.

Границы обследуемого объекта определены в таблице 1. Внутри границ находится информационная поддержка выбора и учёта блюда. Закупка, доставка, приготовление, лабораторное определение состава продуктов и медицинская диагностика в систему не включаются. Такой выбор позволяет сформулировать измеримые требования к данным и решениям, не приписывая системе контроль внешних действий.''')
table('Границы объекта автоматизации',['Элемент','Содержание и ограничение'],[
 ['Входы','Антропометрические параметры, активность, цель, продукты, ограничения, параметры запроса'],
 ['Управляющие сведения','Правила расчёта энергии и БЖУ, справочники, допустимые диапазоны и права доступа'],
 ['Результаты','Проверенный рецепт, расчёт состава, история, оценка пользователя, отчёт по рациону'],
 ['Внешняя среда','Человек подтверждает выбор и самостоятельно выполняет приготовление и учёт'],
 ['Исключения из границ','Назначение лечения, контроль фактического потребления, оплата и доставка продуктов']],[40,130])
text('''Обследование строится на анализе предметной информации и сценарной проверке расчётных гипотез на исследовательском макете. Состав анализируемых сведений приведён в приложении А, процедура и результаты проверки гипотез — в приложении Б. Подготовленный опросник для дальнейшего уточнения требований помещён в приложение В; ответы предполагаемых пользователей не выдумываются и в качестве полученных данных не приводятся.''')

page('Исходный процесс')
text("""Исходный ручной процесс подбора одного блюда представлен на рисунке 1. Человек определяет цель питания, ищет рецепт по доступным продуктам, рассчитывает пищевую ценность и проверяет ограничения. При неподходящем составе поиск и расчёт повторяются.""")
figure('as-is','Процесс ручного подбора рецепта',maxheight=177)
text("""Недостаток процесса заключается в разрыве между поиском, проверкой, пересчётом и учётом. Замена ингредиента требует повторной проверки состава и расчёта. Проектируемая последовательность генерации показана на рисунке И.3, а информационные потоки — на рисунке И.6. Автоматизация должна связать эти действия и сохранить решение пользователя отдельно от предложенного варианта.""")

page('1.2 Обоснование необходимости автоматизации')
h('1.2 Обоснование необходимости автоматизации',2)
text('''Автоматизация необходима для устранения повторяющихся операций над одними и теми же сведениями. Проблемы исходного процесса и соответствующие решения представлены в таблице 2. Связь проблемы с функцией системы позволяет отделить обязательные возможности от дополнений, не влияющих на основной результат.''')
table('Проблемы исходного процесса и направления автоматизации',['Проблема','Последствие','Проектное решение'],[
 ['Раздельное хранение параметров и продуктов','Повторный ввод, несогласованные версии данных','Единый профиль и персональный реестр продуктов'],
 ['Проверка запретов вручную','Неучтённый аллерген или компонент составного продукта','Единая проверка ингредиентов, аллергенов и состава'],
 ['Пересчёт после замены продукта','Расхождение калорийности и массы порции','Серверный расчёт по справочнику на 100 г'],
 ['Поиск без учёта доступной массы','Рецепт требует отсутствующих продуктов','Ограничения на набор и верхние границы массы'],
 ['Неявное включение варианта в рацион','Предложения смешиваются с выбранными блюдами','Разделение статусов «сгенерирован» и «принят»'],
 ['Разрозненная история','Нет воспроизводимого анализа периода','История запросов, рецептов и отчётов']],[48,58,64])
text('''Смысл автоматизации состоит не в увеличении числа предлагаемых блюд, а в согласовании условий выбора. Даже привлекательный рецепт не является пригодным результатом, если не объяснён конфликт с запретом или отсутствует расчёт по выбранной массе. Поэтому проверка ограничений и расчёт выполняются после генерации независимо от источника текста.

Ожидаемое сокращение ручных действий является проектной гипотезой. Исходные документы не содержат подтверждённого хронометража работы человека, поэтому проценты экономии времени не назначаются как достигнутые значения. Для последующей оценки следует измерять полный цикл одного подбора, число повторных вводов и количество возвратов к поиску на одинаковых контрольных сценариях.''')

page('1.3 Назначение проектируемой системы')
h('1.3 Назначение проектируемой системы',2)
text('''АС ГРСН предназначена для персонализированного формирования рецептов спортивного питания и информационной поддержки учёта рациона. Система объединяет профиль человека, справочник пищевой ценности, ограничения, доступные продукты и историю выбора. Пользователь получает несколько вариантов блюда, проверяет состав и принимает выбранный вариант в рацион [1; 2].

Контекст взаимодействия представлен на рисунке Е.1. Пользователь работает через браузер, администратор поддерживает общие данные, а внешняя модель используется как источник предложения рецепта. Прямое взаимодействие пользователя с базой данных не предусматривается.''')
text('''Система хранит расчётный результат вместе с исходными условиями запроса и источником генерации. Она должна явно сообщать об отказе, локальном резервном режиме и обнаруженных несоответствиях. Данные отчёта относятся к принятым рецептам и не доказывают фактическое употребление блюда. Такое ограничение учитывается при интерпретации анализа рациона и прогнозных показателей.''')

page('1.4 Цели создания проектируемой системы')
h('1.4 Цели создания проектируемой системы',2)
text('''Цель создания системы — обеспечить последовательный и прослеживаемый выбор блюда с учётом параметров человека и заданных ограничений. Подцели сформулированы как проверяемые результаты, а не как перечень технологий. В таблице 3 указаны условия, по которым можно оценить достижение каждой подцели при приёмке.''')
table('Цели и критерии достижения',['Код','Подцель','Критерий проверки'],[
 ['Ц1','Исключить повторный ввод постоянных параметров','Сохранённый профиль и продукты доступны в следующем сеансе'],
 ['Ц2','Согласовать рецепт с ограничениями','Контрольные запреты проверяются до и после генерации; конфликт сопровождается причиной'],
 ['Ц3','Обеспечить воспроизводимый расчёт','Повторный расчёт по тем же массам и справочнику даёт одинаковые итоги с принятой точностью'],
 ['Ц4','Разделить предложение и выбор пользователя','Новый вариант хранится в истории; в отчёт входит только после принятия'],
 ['Ц5','Обеспечить анализ выбранного рациона','Итоги за период воспроизводятся из принятых рецептов и правил группировки дат'],
 ['Ц6','Сохранить управляемость при отказе генератора','Источник результата обозначен; при невозможности подбора выдан объяснимый отказ']],[14,62,94])
text('''Для оценки эффективности на следующем этапе следует сопоставить ручной и автоматизированный подбор на одинаковых исходных наборах. При этом необходимо раздельно учитывать время человека, ожидание внешнего генератора и серверную обработку. Наблюдение отдельных запросов исследовательского макета не заменяет такую оценку и не служит подтверждением предельной производительности.

Критерий пригодности результата включает наличие состава, массы ингредиентов, инструкции приготовления, расчёта пищевой ценности и сведений о проверке запретов. Требование точного совпадения с целевой энергией не устанавливается для любого произвольного набора: ограниченный запас продуктов может сделать задачу недостижимой. В таком случае результатом должна быть информация о причинах и допустимых действиях пользователя.''')

for part in ['part2.py','part3_original.py','part_end.py']:
    source=Path(__file__).with_name(part)
    exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),globals())
