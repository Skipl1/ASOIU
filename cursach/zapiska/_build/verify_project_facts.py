"""Audit the saved Word artifact against the supplied project sources.

This complements verify_original_assets.py (images, schemas, equations,
approved forms, appendix content, pagination and unchanged source PDFs).
"""
from pathlib import Path
import json,re,zipfile
from lxml import etree as E

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[1]
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
manifest=json.loads((BASE/'_build/source-assets-manifest.json').read_text(encoding='utf-8'))
output=Path(manifest['output'])
with zipfile.ZipFile(output) as package:root=E.fromstring(package.read('word/document.xml'))
body=root.find('w:body',ns)
def txt(node):return ''.join(node.xpath('.//w:t/text()',namespaces=ns))
def compact(value):return re.sub(r'[\s:;,.()—–−«»`]+','',value).casefold()
paragraphs=[txt(p) for p in body.findall('w:p',ns)]
alltext='\n'.join(root.xpath('//w:t/text()',namespaces=ns))
allcompact=compact(alltext)
tz=(REPO/'Optimization-Methods/lab2 copy/content.typ').read_text(encoding='utf-8')
tp=(REPO/'Optimization-Methods/laba_2/content.typ').read_text(encoding='utf-8')
source_nsi=(REPO/'Optimization-Methods/laba_2/nsi_templates/Шаблоны_справочников_и_НСИ.md').read_text(encoding='utf-8')

tables={}
for i,node in enumerate(body):
    if node.tag!='{'+ns['w']+'}p':continue
    title=txt(node)
    if not (re.match(r'Таблица \d+ – ',title) or title=='Продолжение таблицы 23'):continue
    if i+1<len(body) and body[i+1].tag=='{'+ns['w']+'}tbl':
        rows=[[txt(c) for c in tr.findall('w:tc',ns)] for tr in body[i+1].findall('w:tr',ns)]
        tables[title]=rows
def table(number):
    return next(rows for title,rows in tables.items() if title.startswith('Таблица '+str(number)+' – '))

checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)

# Minimum hardware values are read from the actual source, not inferred from
# runtime Docker settings or an independently chosen deployment profile.
hardware=tz.split('=== 4.5 Требования к техническому обеспечению',1)[1].split('=== 4.6',1)[0]
server_source=hardware.split('*Сервер:*',1)[1].split('*Клиентское устройство:*',1)[0]
client_source=hardware.split('*Клиентское устройство:*',1)[1]
rows={r[0]:r[1] for r in table(8)[1:]}
for key,source in [('Сервер',server_source),('Клиентское устройство',client_source)]:
    for label in ['процессор','оперативная память']:
        requirement=re.search(label+r': ([^;\n]+)',source).group(1)
        check(key+' '+label,compact(label+' '+requirement) in compact(rows[key]))
    speed=re.search(r'со скоростью (от \d+ Мбит/с)',source).group(1)
    check(key+' сеть',compact(speed) in compact(rows[key]))
disk=re.search(r'дисковое пространство: ([^;\n]+)',server_source).group(1)
resolution=re.search(r'разрешение (от [^;\n]+)',client_source).group(1)
check('Диск сервера',compact(disk) in compact(rows['Сервер']))
check('Дисплей клиента',compact(resolution) in compact(rows['Клиентское устройство']))
check('Отсутствуют подменённые минимумы',not re.search(r'от 4 ядер|ОЗУ от 8 ГБ|SSD от 40 ГБ|64-разрядный процессор',alltext))

software=' '.join(' '.join(r) for r in table(10))
for name in ['Docker','Docker Compose','Python','FastAPI','PostgreSQL','Nginx','Uvicorn','Google Chrome','Mozilla Firefox','Microsoft Edge','Яндекс.Браузер']:
    pattern=re.escape(name)+r' \d+(?:\.\d+)* и выше'
    requirement=re.search(pattern,tz).group(0)
    check('Версия '+name,compact(requirement) in compact(software))
for phrase in ['React 18.2.0','HTML5','CSS3','JavaScript (ES6+)','Debian 12','Alpine Linux','Windows 10/11','macOS 11 (Big Sur) и выше','Android 10 и выше']:
    check('Платформа '+phrase,compact(phrase) in compact(tz) and compact(phrase) in compact(software))

obj=re.search(r'Объект автоматизации: ([^\n]+)',tz).group(1)
check('Объект автоматизации',compact(obj) in allcompact)
check('Нет неподтверждённой глубины 5',not re.search(r'пятью уровнями|пять уровней|глубина[^.]{0,80}\b5\b',alltext,re.I))
check('Нет выдуманной семантики даты отчёта','Период определяется датой создания записи' not in alltext)
check('Нет отложенного выбора браузеров','набор поддерживаемых версий фиксируется перед развёртыванием' not in alltext)

perf=next(p for p in paragraphs if 'Отклик при одиночном запросе' in p)
for phrase in ['GigaChat-2-Pro','не более 30 секунд','не более 60 секунд','более 30 секунд','за 5 секунд','100 пользователей','100 одновременных пользователей']:
    check('Производительность '+phrase,compact(phrase) in compact(perf))
check('Показатели не выданы за результат испытаний',any('нагрузочными испытаниями' in p and 'не подтверждается' in p for p in paragraphs))
backup=next(p for p in paragraphs if 'pg_dump' in p)
for phrase in ['Ежедневно','pg_dump','cron','отдельном диске сервера','30 дней','автоматически']:
    check('Резервирование '+phrase,compact(phrase) in compact(backup))
auth=next(p for p in paragraphs if 'По умолчанию срок действия JWT' in p)
for phrase in ['30 минут','пяти неудачных попыток','15 минут','задаются настройками','72 байта','expiresIn']:
    check('Вход '+phrase,phrase in auth)

limits=' '.join(' '.join(r) for r in table(23)+tables['Продолжение таблицы 23'])
for phrase in ['1–120','255','8 символов','72 байт','30–300','100–250','14–100','1–160','100 000 г','300 позиций','500 символов','3 допустимых','8 г на 100 г','300 г','250 г','200 г','350 г','400 г','40 г','30 г','3–200','1–20','5000 г','3–20','1000 символов','366 дней','950 ккал']:
    check('Ограничение '+phrase,compact(phrase) in compact(limits))
for number in ['100~000','300~позиций','500~символов','5000~г','1000~символов','366~дней','950~ккал']:
    check('Ограничение подтверждено источником '+number,number in tz)
for phrase in ['4–5 баллов','1–2','GigaChat-2-Pro','не менее трёх рекомендуемых ингредиентов','не менее чем из трёх шагов','не настроен']:
    check('Генерация '+phrase,compact(phrase) in allcompact)

# Validate every code/name and every published nutritional value, and ensure
# abbreviated allergen examples are genuine subsets of the source lists.
nsi_rows={}
for line in source_nsi.splitlines():
    if not line.startswith('|'):continue
    cells=[c.strip().strip('`') for c in line.strip('|').split('|')]
    if cells:nsi_rows.setdefault(cells[0],cells)
check('Каталог 65 ингредиентов',sum(k.startswith('ing_') for k in nsi_rows)==65)
counts={'goals':0,'categories':0,'allergens':0,'ingredients':0}
for r in table(12)[1:]:
    src=nsi_rows[r[0]]
    check('Цель '+r[0],r[1]==src[1] and compact(r[2])==compact(src[3]) and compact(r[3])==compact(' / '.join(src[4:7])))
    counts['goals']+=1
for r in table(13)[1:]:
    check('Категория '+r[0],r[1]==nsi_rows[r[0]][1]);counts['categories']+=1
for r in table(14)[1:]:
    src=nsi_rows[r[0]]
    check('Аллерген '+r[0],r[1]==src[1] and all(compact(s) in compact(src[3]) for s in r[2].split(',')))
    counts['allergens']+=1
for r in table(16)[1:]:
    src=nsi_rows[r[0]]
    check('Пищевая ценность '+r[0],r[1]==src[1] and compact(r[2])==compact(src[3]) and compact(r[3])==compact(src[4]))
    counts['ingredients']+=1
ingredients_by_name={r[1]:r for key,r in nsi_rows.items() if key.startswith('ing_')}
for r in table(17)[1:]:
    check('Связь состава '+r[0]+' → '+r[1],compact(r[1]) in compact(ingredients_by_name[r[0]][7]))
css=(REPO/'Optimization-Methods/laba_2/mockups/styles.css').read_text(encoding='utf-8')
for color in set(re.findall(r'#[0-9A-Fa-f]{6}',alltext)):
    check('Цвет '+color,color.casefold() in css.casefold())

result={'output':str(output),'checks_passed':len(checks),'checked_hardware_and_network_minima':True,'checked_software_platforms_and_versions':True,'checked_project_scope':True,'checked_performance_and_backups':True,'checked_auth_defaults':True,'checked_input_limits_and_generation_rules':True,'checked_nsi_rows':counts,'checked_composition_links':len(table(17))-1,'all_checks':checks}
(BASE/'_build/project-facts-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='all_checks'},ensure_ascii=False,indent=2))
