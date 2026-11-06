from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parents[1] / 'assets'
BASE = 'html=1;fontFamily=Arial;fontColor=#000000;strokeColor=#000000;fillColor=#FFFFFF;strokeWidth=1.3;'


class Model:
    def __init__(self, name, width=980, height=800):
        self.name = name
        self.file = ET.Element('mxfile', {'host': 'app.diagrams.net', 'type': 'device'})
        diagram = ET.SubElement(self.file, 'diagram', {'name': name, 'id': name})
        graph = ET.SubElement(diagram, 'mxGraphModel', {
            'dx': str(width), 'dy': str(height), 'grid': '1', 'gridSize': '10',
            'page': '0', 'pageWidth': str(width), 'pageHeight': str(height),
            'background': '#FFFFFF', 'shadow': '0',
        })
        self.root = ET.SubElement(graph, 'root')
        ET.SubElement(self.root, 'mxCell', {'id': '0'})
        ET.SubElement(self.root, 'mxCell', {'id': '1', 'parent': '0'})

    def node(self, id, title, lines, x, y, w, h, font=20):
        c = ET.SubElement(self.root, 'mxCell', {
            'id': id, 'value': title, 'vertex': '1', 'parent': '1',
            'style': BASE + 'swimlane;startSize=38;collapsible=0;container=1;pointerEvents=0;'
                     'fontStyle=1;fontSize=21;whiteSpace=wrap;',
        })
        ET.SubElement(c, 'mxGeometry', {'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h), 'as': 'geometry'})
        body = ET.SubElement(self.root, 'mxCell', {
            'id': id + '_body', 'value': '<br>'.join(lines), 'vertex': '1', 'parent': id,
            'style': BASE + f'text;strokeColor=none;fillColor=none;fontStyle=0;fontSize={font};'
                     'whiteSpace=wrap;align=left;verticalAlign=middle;spacingLeft=12;spacingRight=10;',
        })
        ET.SubElement(body, 'mxGeometry', {'x': '0', 'y': '38', 'width': str(w), 'height': str(h - 38), 'as': 'geometry'})

    def edge(self, id, source, target, mults, ports, points=(), role='', vertical=False):
        ex, ey, ix, iy = ports
        c = ET.SubElement(self.root, 'mxCell', {
            'id': id, 'source': source, 'target': target, 'edge': '1', 'parent': '1', 'value': role,
            'style': BASE + 'edgeStyle=orthogonalEdgeStyle;rounded=0;endArrow=none;fontSize=18;'
                     'defaultLabelBackgroundColor=page;labelBackgroundColor=#FFFFFF;'
                     f'exitX={ex};exitY={ey};entryX={ix};entryY={iy};',
        })
        geo = ET.SubElement(c, 'mxGeometry', {'relative': '1', 'as': 'geometry'})
        if points:
            arr = ET.SubElement(geo, 'Array', {'as': 'points'})
            for x, y in points:
                ET.SubElement(arr, 'mxPoint', {'x': str(x), 'y': str(y)})
        for i, (position, value) in enumerate(zip((-.87, .87), mults)):
            label = ET.SubElement(self.root, 'mxCell', {
                'id': id + '_m' + str(i), 'value': value, 'vertex': '1', 'connectable': '0', 'parent': id,
                'style': BASE + 'edgeLabel;strokeColor=none;fillColor=#FFFFFF;resizable=0;'
                         'fontSize=19;align=center;verticalAlign=middle;',
            })
            lg = ET.SubElement(label, 'mxGeometry', {'x': str(position), 'y': '0', 'relative': '1', 'as': 'geometry'})
            ET.SubElement(lg, 'mxPoint', {
                'x': '25' if vertical else '0',
                'y': '0' if vertical else ('-16' if i == 0 else '16'), 'as': 'offset',
            })

    def note(self, text, y, h=42):
        c = ET.SubElement(self.root, 'mxCell', {
            'id': 'legend', 'value': text, 'vertex': '1', 'parent': '1',
            'style': BASE + 'text;strokeColor=none;fillColor=none;fontSize=18;align=center;whiteSpace=wrap;',
        })
        ET.SubElement(c, 'mxGeometry', {'x': '15', 'y': str(y), 'width': '950', 'height': str(h), 'as': 'geometry'})

    def save(self):
        ET.indent(self.file, space='  ')
        path = OUT / (self.name + '.drawio')
        ET.ElementTree(self.file).write(path, encoding='utf-8', xml_declaration=True)
        ET.parse(path)
        print(path.name)


def users(physical):
    name = ('physical' if physical else 'logical') + '-users'
    m = Model(name)
    if physical:
        values = {
            'user': ('users', ['PK user_id: uuid', 'name: varchar(120); UQ email', 'password_hash: text', 'role; status; token_version']),
            'profile': ('user_profiles', ['PK profile_id: uuid', 'FK/UQ user_id → users', 'FK fitness_goal_id (NULL)', 'weight_kg; height_cm; age', 'sex; activity_level; updated_at']),
            'goal': ('fitness_goals', ['PK fitness_goal_id: uuid', 'UQ code; UQ name', 'calorie_correction: numeric(8,2)', 'protein_pct; fat_pct; carb_pct']),
            'history': ('parameter_history', ['PK record_id: uuid', 'FK user_id → users', 'weight_kg; height_cm; age', 'activity_level; recorded_at']),
            'available': ('available_ingredients', ['PK/FK user_id → users', 'PK/FK ingredient_id → ingredients', 'available_amount_g: numeric(8,1)', 'updated_at: timestamptz']),
            'restriction': ('user_restrictions', ['PK restriction_id: uuid', 'FK user_id → users', 'FK ingredient_id / allergen_id', 'restriction_type; normalized_name']),
        }
    else:
        values = {
            'user': ('Пользователь', ['Код пользователя (PK)', 'Имя; почта; хеш пароля', 'Роль; статус; версия сеанса']),
            'profile': ('Профиль', ['Код профиля (PK)', 'Пользователь (FK, UNIQUE)', 'Цель (FK, необязательная)', 'Масса; рост; возраст; пол; активность']),
            'goal': ('Цель питания', ['Код цели (PK)', 'Уникальный код; название', 'Поправка энергии; доли БЖУ']),
            'history': ('История параметров', ['Код записи (PK)', 'Пользователь (FK)', 'Параметры; дата измерения']),
            'available': ('Доступный продукт', ['Пользователь (PK, FK)', 'Ингредиент (PK, FK)', 'Доступная масса; дата']),
            'restriction': ('Запрет пользователя', ['Код запрета (PK)', 'Пользователь (FK); тип', 'Ингредиент / аллерген (FK)', 'Исходное и нормализованное имя']),
        }
    positions = {'user': (40, 40), 'profile': (570, 40), 'available': (40, 300),
                 'goal': (570, 300), 'history': (40, 560), 'restriction': (570, 560)}
    for id, (x, y) in positions.items():
        title, lines = values[id]
        m.node(id, title, lines, x, y, 350, 175, 19 if physical else 20)
    m.edge('user_profile', 'user', 'profile', ('1', '0..1'), (1, .5, 0, .5))
    m.edge('goal_profile', 'goal', 'profile', ('0..1', '0..*'), (.5, 0, .5, 1), vertical=True)
    m.edge('user_available', 'user', 'available', ('1', '0..*'), (.5, 1, .5, 0), vertical=True)
    m.edge('user_history', 'user', 'history', ('1', '0..*'), (0, .5, 0, .5), ((10, 127.5), (10, 647.5)))
    m.edge('user_restrictions', 'user', 'restriction', ('1', '0..*'), (1, .86, 0, .5), ((480, 190.5), (480, 647.5)))
    m.note('Кратности указаны у концов связей. Внешние ссылки на каталог раскрыты в модели НСИ.', 760)
    m.save()


def catalog(physical):
    m = Model(('physical' if physical else 'logical') + '-catalog', height=650)
    if physical:
        values = {
            'category': ('ingredient_categories', ['PK category_id: uuid', 'UQ code; UQ name', 'description: text']),
            'ingredient': ('ingredients', ['PK ingredient_id: uuid', 'FK category_id (NULL)', 'UQ code; UQ name', 'БЖУ и ккал на 100 г', 'is_composite; name_synonyms']),
            'allergen': ('allergens', ['PK allergen_id: uuid', 'UQ code; UQ name', 'synonyms: jsonb', 'description: text']),
            'link': ('ingredient_allergens', ['PK/FK ingredient_id', 'PK/FK allergen_id']),
            'component': ('ingredient_components', ['PK/FK composite_id', 'PK/FK component_id', 'CHECK: composite_id', 'не равен component_id']),
        }
    else:
        values = {
            'category': ('Категория', ['Код категории (PK)', 'Уникальный код; название', 'Описание']),
            'ingredient': ('Ингредиент', ['Код ингредиента (PK)', 'Категория (FK, необяз.)', 'Код; имя; БЖУ и ккал', 'Составной; синонимы']),
            'allergen': ('Аллерген', ['Код аллергена (PK)', 'Код; название; описание', 'Синонимы']),
            'link': ('Аллерген ингредиента', ['Ингредиент (PK, FK)', 'Аллерген (PK, FK)']),
            'component': ('Компонент ингредиента', ['Составной продукт (PK, FK)', 'Продукт-компонент (PK, FK)']),
        }
    positions = {'category': (20, 35), 'ingredient': (360, 35), 'allergen': (700, 35),
                 'component': (360, 370), 'link': (700, 370)}
    for id, (x, y) in positions.items():
        title, lines = values[id]
        m.node(id, title, lines, x, y, 260, 205 if id == 'ingredient' else 180, 19)
    m.edge('category_ingredient', 'category', 'ingredient', ('0..1', '0..*'), (1, .5, 0, .44))
    m.edge('allergen_link', 'allergen', 'link', ('1', '0..*'), (.5, 1, .5, 0), vertical=True)
    m.edge('ingredient_link', 'ingredient', 'link', ('1', '0..*'), (1, .85, 0, .7), ((660, 209.25), (660, 496)))
    m.edge('whole_component', 'ingredient', 'component', ('1', '0..*'), (.24, 1, .24, 0), role='целое', vertical=True)
    m.edge('part_component', 'ingredient', 'component', ('1', '0..*'), (.76, 1, .76, 0), role='компонент', vertical=True)
    m.note('Две отдельные связи состава отражают роли целого продукта и компонента.<br>Пищевая ценность относится к 100 г; полный словарь полей приведён в приложении Г.', 585, 55)
    m.save()


def recipes(physical):
    m = Model(('physical' if physical else 'logical') + '-recipes', height=730)
    if physical:
        values = {
            'request': ('generation_requests', ['PK generation_request_id', 'FK user_id; FK fitness_goal_id', 'variant_count; status', 'daily_norm_share', 'provider; duration_ms', 'requested_at']),
            'recipe': ('recipes', ['PK recipe_id', 'FK generation_request_id', 'FK user_id; FK fitness_goal_id', 'generation_status; source', 'calories_kcal; БЖУ', 'cooking_instruction: jsonb']),
            'item': ('recipe_ingredients', ['PK/FK recipe_id', 'PK/FK ingredient_id', 'mass_g: numeric(8,1)', 'list_order: integer']),
            'rating': ('recipe_ratings', ['PK rating_id', 'FK user_id; FK recipe_id', 'UQ(user_id, recipe_id)', 'score: integer (1..5)', 'comment: text; rated_at']),
            'report': ('nutrition_reports', ['PK report_id', 'FK user_id; FK fitness_goal_id', 'period_start; period_end', 'export_format; file_name', 'total_calories; average_calories', 'total_protein_g', 'total_fat_g', 'total_carb_g']),
            'audit': ('audit_log', ['PK log_id', 'FK user_id (NULL) → users', 'action; entity; entity_id', 'details: jsonb', 'ip; created_at: timestamptz']),
        }
    else:
        values = {
            'request': ('Запрос генерации', ['Код запроса (PK)', 'Пользователь; цель (FK)', 'Доля; варианты; статус', 'Источник; длительность', 'Время запроса и завершения']),
            'recipe': ('Рецепт', ['Код рецепта (PK)', 'Запрос (FK, необязательный)', 'Пользователь; цель (FK)', 'Название; БЖУ; ккал; статус', 'Инструкция; источник; даты']),
            'item': ('Ингредиент рецепта', ['Рецепт (PK, FK)', 'Ингредиент (PK, FK)', 'Масса; порядок']),
            'rating': ('Оценка рецепта', ['Код оценки (PK)', 'Рецепт; пользователь (FK)', 'Балл; комментарий; дата', 'Одна оценка пары', '«пользователь — рецепт»']),
            'report': ('Отчёт по рациону', ['Код отчёта (PK)', 'Пользователь; цель (FK)', 'Период; формат', 'Итоги; файл; дата']),
            'audit': ('Событие аудита', ['Код события (PK)', 'Пользователь (FK, необяз.)', 'Действие; объект; детали', 'IP-адрес; дата']),
        }
    positions = {'request': (20, 35), 'recipe': (360, 35), 'item': (700, 35),
                 'report': (20, 415), 'rating': (360, 415), 'audit': (700, 415)}
    for id, (x, y) in positions.items():
        title, lines = values[id]
        m.node(id, title, lines, x, y, 260, 220, 18 if physical else 19)
    m.edge('request_recipe', 'request', 'recipe', ('0..1', '0..*'), (1, .5, 0, .5))
    m.edge('recipe_item', 'recipe', 'item', ('1', '1..*'), (1, .5, 0, .5))
    m.edge('recipe_rating', 'recipe', 'rating', ('1', '0..*'), (.5, 1, .5, 0), vertical=True)
    m.note('Связи с пользователем, целью и каталогом указаны полями FK.<br>UUID — тип идентификаторов; полный состав и точные типы полей — в приложении Г.', 670, 55)
    m.save()


if __name__ == '__main__':
    for physical in (False, True):
        users(physical)
        catalog(physical)
        recipes(physical)
