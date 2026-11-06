from pathlib import Path
import xml.etree.ElementTree as ET
import subprocess
import html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
CLI = r'C:\Users\abdul\AppData\Local\Programs\draw.io\draw.io.exe'

class Drawing:
    def __init__(self, name, width=820, height=520):
        self.name=name
        self.root=ET.Element('mxfile', host='app.diagrams.net')
        dia=ET.SubElement(self.root,'diagram',name=name,id=name)
        model=ET.SubElement(dia,'mxGraphModel',dx=str(width),dy=str(height),grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(width),pageHeight=str(height),background='#ffffff')
        self.cells=ET.SubElement(model,'root')
        ET.SubElement(self.cells,'mxCell',id='0')
        ET.SubElement(self.cells,'mxCell',id='1',parent='0')
        self.n=1
    def box(self,text,x,y,w,h,style='',fill='#ffffff',font=18):
        self.n+=1; id=str(self.n)
        s=f'rounded=0;whiteSpace=wrap;html=0;align=left;verticalAlign=middle;spacingLeft=10;spacingRight=7;fontFamily=Arial;fontSize={font};fontColor=#111827;strokeColor=#64748b;fillColor={fill};'+style
        c=ET.SubElement(self.cells,'mxCell',id=id,value=text,style=s,vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
        return id
    def line(self,a,b,text='',style=''):
        self.n+=1
        c=ET.SubElement(self.cells,'mxCell',id=str(self.n),value=text,style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;fontFamily=Arial;fontSize=17;labelBackgroundColor=#ffffff;endArrow=block;endFill=0;strokeColor=#334155;'+style,edge='1',parent='1',source=a,target=b)
        ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
    def write(self):
        p=OUT/(self.name+'.drawio')
        ET.ElementTree(self.root).write(p,encoding='utf-8',xml_declaration=True)
        subprocess.run([CLI,'--disable-gpu','--export','--format','png','--embed-diagram','--scale','2','--border','12','--output',str(p.with_suffix('.drawio.png')),str(p)],check=True,stdout=subprocess.DEVNULL,creationflags=0x08000000)

def header(d,title,active=''):
    d.box('АС ГРСН   /   '+title,10,10,800,48,'fontStyle=1;',fill='#e8eefc',font=23)
    d.box('Профиль  |  Запреты  |  Продукты  |  Рецепты  |  История  |  Отчёты',10,65,800,36,'strokeColor=none;',font=17)

def btn(d,text,x,y,w=190):
    d.box(text,x,y,w,40,'align=center;fontStyle=1;',fill='#dbeafe')

def field(d,label,x,y,w=360,placeholder='Выберите или введите значение'):
    d.box(label,x,y,w,24,'strokeColor=none;',font=17)
    d.box(placeholder,x,y+27,w,40,fill='#f8fafc',font=17)

def ui(name,title,fields,buttons,note='',height=445):
    d=Drawing(name,height=height);header(d,title)
    for i,(label,ph) in enumerate(fields): field(d,label,30+(i%2)*395,115+(i//2)*92,365,ph)
    yy=125+((len(fields)+1)//2)*92
    for i,t in enumerate(buttons): btn(d,t,30+i*255,yy,235)
    if note: d.box(note,30,yy+52,760,52,'strokeColor=none;',font=17)
    d.write()

def main():
    ui('mock-login','Вход в систему',[('Электронная почта','name@example.ru'),('Пароль','••••••••')],['Войти','Создать учётную запись'],'Неверные данные → общее сообщение без раскрытия наличия учётной записи.',350)
    ui('mock-register','Регистрация',[('Имя','Введите имя'),('Электронная почта','name@example.ru'),('Пароль','Не менее 8 символов: буква и цифра'),('Повтор пароля','Повторите пароль')],['Зарегистрироваться','Перейти ко входу'],'Ошибка поля отображается рядом с ним. Пароль при ошибке не показывается.',450)
    ui('mock-profile','Профиль и цель питания',[('Масса, кг / рост, см','Числовые поля'),('Возраст / пол','Возраст; выбор пола'),('Физическая активность','Список из пяти уровней'),('Фитнес-ориентир','Список из четырёх целей')],['Сохранить профиль','История параметров'],'После проверки: расчёт суточной энергии и целевых долей БЖУ.',450)
    ui('mock-restrictions','Ограничения',[('Тип запрета','Ингредиент / аллерген / название'),('Объект запрета','Поиск в справочнике или текст')],['Добавить запрет','Проверить набор'],'Список запретов: объект | тип | удалить. Конфликт объясняется до генерации.',350)
    d=Drawing('mock-ingredients',height=460);header(d,'Каталог и доступные продукты')
    field(d,'Поиск по названию или синониму',30,110,365,'Введите поисковый запрос');field(d,'Категория',425,110,365,'Все категории ▾')
    d.box('Выбор | Продукт | Б / Ж / У на 100 г | Ккал | Доступно, г',30,195,760,40,'fontStyle=1;',fill='#f1f5f9')
    for j in range(3): d.box('□       Наименование        Значения из НСИ        Число или без лимита',30,235+j*40,760,40,font=17)
    btn(d,'Сохранить набор',30,370,250);d.box('Запрещённые позиции обозначены текстом и недоступны для выбора.',30,420,760,30,'strokeColor=none;',font=17);d.write()
    ui('mock-generate','Запрос рецепта',[('Приём пищи / доля нормы','Выберите приём пищи; доля от 0 до 1'),('Число вариантов / сложность','От 1 до 3; низкая / средняя / высокая'),('Комментарий','Необязательные предпочтения'),('Цель запроса','Фитнес-ориентир из профиля')],['Проверить условия','Сгенерировать'],'При недостаточном наборе — причина отказа и список допустимых дополнений.',450)
    d=Drawing('mock-result',height=460);header(d,'Результат генерации')
    d.box('Название рецепта   |   Вариант 1 из N',30,115,760,42,'fontStyle=1;',fill='#f1f5f9')
    d.box('Пищевая ценность: Б, г | Ж, г | У, г | энергия, ккал\nЦелевая энергия и отклонение; источник: GigaChat / локальный',30,170,760,65)
    d.box('Состав: ингредиент — масса, г\nПриготовление: последовательность шагов\nОграничения: проверены / обнаружено несоответствие с пояснением',30,247,760,100)
    btn(d,'Добавить в рацион',30,365,260);btn(d,'Другой вариант',320,365,230)
    d.box('Сгенерированный вариант уже хранится в истории. В отчёт входит после принятия.',30,416,760,35,'strokeColor=none;',font=17);d.write()
    d=Drawing('mock-history',height=435);header(d,'История рецептов')
    field(d,'Период',30,110,365,'Начало — конец');field(d,'Статус / цель',425,110,365,'Любой статус; любой ориентир')
    d.box('Дата | Рецепт | Энергия | Статус | Оценка | Действия',30,195,760,40,'fontStyle=1;',fill='#f1f5f9')
    for j in range(3):d.box('Дата       Название       ккал       Статус        1–5       Открыть',30,235+j*38,760,38,font=17)
    btn(d,'Применить фильтр',30,365,250);btn(d,'Оценить рецепт',315,365,230);d.write()
    ui('mock-reports','Отчёты по рациону',[('Начало / конец периода','Даты в допустимом порядке'),('Формат выгрузки','PDF / XLSX / CSV')],['Сформировать','Скачать файл'],'Итоги: принятые рецепты, энергия, БЖУ, число дней с записями; при пустоте — пояснение.',350)
    d=Drawing('mock-analysis',height=430);header(d,'Анализ соответствия цели')
    d.box('История параметров: текущая масса | предыдущая масса | динамика',30,115,760,55,fill='#f1f5f9')
    d.box('Показатель          Цель          Учтено          Отклонение\nЭнергия                ккал           ккал                  %\nБелки / жиры / углеводы: граммы и доли энергии',30,185,760,100)
    d.box('Прогноз на 30 дней: расчётная оценка при сохранении энергетического баланса.\nНеполный рацион и пропущенные дни ограничивают интерпретацию.',30,300,760,65)
    btn(d,'Обновить анализ',30,380,250);d.write()
    d=Drawing('mock-admin',height=425);header(d,'Администрирование')
    d.box('Пользователи | Цели | Категории | Ингредиенты | Аллергены | Журнал',30,115,760,40,'fontStyle=1;',fill='#f1f5f9')
    d.box('Поиск / фильтр статуса           [Запрос]                 [Найти]',30,170,760,40)
    d.box('Пользователь | Роль | Статус | Изменить роль | Блокировать\nКарточка записи открывается после выбора строки.\nОпасное действие требует подтверждения и записывается в журнал.',30,225,760,105)
    btn(d,'Создать запись НСИ',30,350,270);btn(d,'Открыть журнал',330,350,250);d.write()
    ui('mock-nsi','Карточка ингредиента (администратор)',[('Код / наименование','ing_…; уникальное название'),('Категория / синонимы','Выбор категории; список названий'),('Белки / жиры / углеводы','Граммы на 100 г, неотрицательные'),('Энергия / состав / аллергены','Ккал на 100 г; связанные записи')],['Проверить и сохранить','Отмена'],'Сумма БЖУ ≤ 100 г. Ошибки у поля. Компонент не может ссылаться сам на себя.',450)
    d=Drawing('mock-messages',height=365);header(d,'Состояния и сообщения')
    msgs=[('Ошибка поля','«Укажите массу от 30 до 300 кг» — исправить выделенное поле.'),('Нельзя выполнить','«Недостаточно допустимых продуктов» — изменить набор, сохранить запреты.'),('Информация','«Использован локальный генератор» — показать источник в карточке.'),('Подтверждение','«Заблокировать учётную запись?» — Подтвердить / Отмена.')]
    for i,(a,b) in enumerate(msgs):d.box(a+': '+b,30,112+i*60,760,52,fill='#f8fafc',font=17)
    d.write()
    # Logical model divided into readable views; all entity and attribute names are Russian.
    groups=[('logical-users',[
        ('Пользователь','Код пользователя (PK)\nИмя; почта; хеш пароля\nРоль; статус; версия сеанса'),
        ('Профиль','Код профиля (PK)\nПользователь (FK, UNIQUE)\nЦель (FK); масса; рост; возраст\nПол; коэффициент активности'),
        ('Цель питания','Код цели (PK)\nУникальный код; название\nПоправка энергии; доли БЖУ'),
        ('История параметров','Код записи (PK)\nПользователь (FK)\nПараметры; дата измерения'),
        ('Доступный продукт','Пользователь (PK, FK)\nИнгредиент (PK, FK)\nДоступная масса; дата'),
        ('Запрет пользователя','Код запрета (PK)\nПользователь (FK); тип\nИнгредиент / аллерген (FK)\nИсходное и нормализованное имя')],[(0,1,'1 : 0..1'),(2,1,'1 : 0..N'),(0,3,'1 : 0..N'),(0,4,'1 : 0..N'),(0,5,'1 : 0..N')]),
      ('logical-catalog',[
        ('Категория','Код категории (PK)\nУникальный код; название\nОписание'),
        ('Ингредиент','Код ингредиента (PK)\nКатегория (FK); код; имя\nБЖУ и энергия на 100 г\nПризнак составного; синонимы'),
        ('Аллерген','Код аллергена (PK)\nКод; название; описание\nСинонимы'),
        ('Аллерген ингредиента','Ингредиент (PK, FK)\nАллерген (PK, FK)'),
        ('Компонент ингредиента','Составной продукт (PK, FK)\nПродукт-компонент (PK, FK)')],[(0,1,'1 : 0..N'),(1,3,'1 : 0..N'),(2,3,'1 : 0..N'),(1,4,'1 : 0..N (две роли)')]),
      ('logical-recipes',[
        ('Запрос генерации','Код запроса (PK)\nПользователь; цель (FK)\nДоля; число вариантов; статус\nИсточник; длительность; даты'),
        ('Рецепт','Код рецепта (PK)\nЗапрос; пользователь; цель (FK)\nНазвание; БЖУ; энергия; статус\nИнструкция; источник; даты'),
        ('Ингредиент рецепта','Рецепт (PK, FK)\nИнгредиент (PK, FK)\nМасса; порядок'),
        ('Оценка рецепта','Код оценки (PK)\nРецепт; пользователь (FK)\nБалл; комментарий; дата'),
        ('Отчёт по рациону','Код отчёта (PK)\nПользователь; цель (FK)\nПериод; формат; итоги; файл'),
        ('Событие аудита','Код события (PK)\nПользователь (FK, необяз.)\nДействие; объект; детали; дата')],[(0,1,'1 : 0..N'),(1,2,'1 : 1..N'),(1,3,'1 : 0..N')])]
    for name,entities,edges in groups:
        d=Drawing(name,width=820,height=650);ids=[]
        for i,(title,attrs) in enumerate(entities):
            x=15+(i%2)*410;y=20+(i//2)*210
            ids.append(d.box(title+'\n──────────────\n'+attrs,x,y,375,165,'verticalAlign=top;spacingTop=9;',font=18))
        for a,b,t in edges:d.line(ids[a],ids[b],t,'endArrow=none;')
        d.write()
    # Physical model views: the complete column catalogue is supplied separately in Word.
    physical=[('physical-users',[
      ('users','PK user_id: uuid\nUQ email: varchar(255)\nrole, status: varchar(20)\npassword_hash: text; token_version: int'),
      ('user_profiles','PK profile_id: uuid\nFK/UQ user_id → users\nFK fitness_goal_id → fitness_goals\nweight_kg; height_cm; age; sex; activity_level'),
      ('fitness_goals','PK fitness_goal_id: uuid\nUQ code; UQ name\ncalorie_correction: numeric\nprotein_pct; fat_pct; carb_pct'),
      ('parameter_history','PK record_id: uuid\nFK user_id → users\nweight_kg; height_cm; age\nactivity_level; recorded_at: timestamptz'),
      ('available_ingredients','PK/FK user_id → users\nPK/FK ingredient_id → ingredients\navailable_amount_g: numeric(8,1)\nupdated_at: timestamptz'),
      ('user_restrictions','PK restriction_id: uuid\nFK user_id → users\nFK ingredient_id / allergen_id\nrestriction_type; normalized_name')],[(0,1,'1 : 0..1'),(2,1,'1 : N'),(0,3,'1 : N'),(0,4,'1 : N'),(0,5,'1 : N')]),
      ('physical-catalog',[
      ('ingredient_categories','PK category_id: uuid\nUQ code; UQ name\ndescription: text'),
      ('ingredients','PK ingredient_id: uuid\nFK category_id → ingredient_categories\nUQ code; UQ name\nprotein/fat/carb/calories_per_100g: numeric'),
      ('allergens','PK allergen_id: uuid\nUQ code; UQ name\nsynonyms: jsonb; description: text'),
      ('ingredient_allergens','PK/FK ingredient_id → ingredients\nPK/FK allergen_id → allergens'),
      ('ingredient_components','PK/FK composite_id → ingredients\nPK/FK component_id → ingredients\nCHECK composite_id ≠ component_id')],[(0,1,'1 : N'),(1,3,'1 : N'),(2,3,'1 : N'),(1,4,'1 : N (2 FK)')]),
      ('physical-recipes',[
      ('generation_requests','PK generation_request_id: uuid\nFK user_id; FK fitness_goal_id\nvariant_count; daily_norm_share; status\nprovider; duration_ms; requested_at'),
      ('recipes','PK recipe_id: uuid\nFK generation_request_id; user_id; goal\ngeneration_status; calories_kcal; БЖУ\ncooking_instruction: jsonb; created_at'),
      ('recipe_ingredients','PK/FK recipe_id → recipes\nPK/FK ingredient_id → ingredients\nmass_g: numeric(8,1); list_order: int'),
      ('recipe_ratings','PK rating_id: uuid\nFK user_id; FK recipe_id\nUQ (user_id, recipe_id)\nscore: int; comment: text; rated_at'),
      ('nutrition_reports','PK report_id: uuid\nFK user_id; FK fitness_goal_id\nperiod_start/end: date; export_format\ntotals: numeric; file_name: varchar'),
      ('audit_log','PK log_id: uuid\nFK user_id → users (nullable)\naction; entity; entity_id; details: jsonb\nip; created_at: timestamptz')],[(0,1,'1 : N'),(1,2,'1 : N'),(1,3,'1 : N')])]
    for name,entities,edges in physical:
        d=Drawing(name,width=820,height=650);ids=[]
        for i,(title,attrs) in enumerate(entities):
            ids.append(d.box(title+'\n────────────\n'+attrs,15+(i%2)*410,20+(i//2)*210,375,170,'verticalAlign=top;spacingTop=9;',font=17))
        for a,b,t in edges:d.line(ids[a],ids[b],t,'endArrow=none;')
        d.write()
    for name,role,msgs in [
      ('auth-user','Пользователь',[(0,1,'1 Ввод почты и пароля'),(1,2,'2 Передать данные входа'),(2,2,'3 Проверить хеш и статус'),(2,1,'4 JWT и роль / отказ'),(1,0,'5 Профиль или сообщение'),(0,1,'6 Запрос личных данных'),(1,2,'7 JWT + запрос ресурса'),(2,1,'8 Данные только владельца')]),
      ('auth-admin','Администратор',[(0,1,'1 Войти по личной записи'),(1,2,'2 Проверить пароль и статус'),(2,1,'3 JWT с ролью admin'),(0,1,'4 Открыть управление'),(1,2,'5 Проверить роль и версию JWT'),(2,1,'6 Данные / 403 для другой роли'),(0,1,'7 Подтвердить изменение НСИ'),(1,2,'8 Проверить, сохранить, аудит')])]:
        d=Drawing(name,width=820,height=650)
        for j,t in enumerate([role,'Веб-интерфейс','Сервер и БД']):
            x=20+j*280;d.box(t,x,10,220,45,'align=center;fontStyle=1;',fill='#f1f5f9')
            a=d.box('',x+109,65,2,560,'strokeColor=#94a3b8;fillColor=#94a3b8;')
        for i,(a,b,txt) in enumerate(msgs):
            y=100+i*63
            if a==b:
                d.box(txt,565,y-15,240,48,'strokeColor=none;',font=17)
                continue
            aa=d.box('',130+a*280,y,1,1,'strokeColor=none;fillColor=none;')
            bb=d.box('',130+b*280,y,1,1,'strokeColor=none;fillColor=none;')
            d.line(aa,bb,txt,'edgeStyle=none;endArrow=classic;endFill=1;fontSize=17;verticalLabelPosition=top;verticalAlign=bottom;')
        d.write()

if __name__=='__main__':main()
