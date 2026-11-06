"""Single source of truth for reused, unmodified project illustrations and schema."""
from pathlib import Path
import json

def source_catalog(repo):
    images=repo/'Optimization-Methods/laba_2/images'
    groups=[('Д','Макеты экранов',[
        ('ui-login','Форма входа в систему'),('ui-register','Форма регистрации'),
        ('ui-profile','Профиль и фитнес-ориентир'),('ui-profile-history','История физических параметров'),
        ('ui-restrictions','Запреты и аллергены'),('ui-ingredients','Каталог и доступные ингредиенты'),
        ('ui-generate-form','Форма запроса рецепта'),('ui-generate-result','Результат генерации рецепта'),
        ('ui-history','История рецептов и оценки'),('ui-reports','Отчёт о пищевой ценности'),
        ('ui-analysis','Анализ соответствия рациона цели'),('ui-admin','Администрирование'),
        ('ui-structure','Модель структуры интерфейса')]),
      ('Е','Архитектурные схемы',[
        ('c4-context','Контекстная C4-модель АС ГРСН'),
        ('c4-container','Контейнерная C4-модель АС ГРСН'),
        ('c4-component','Компонентная C4-модель серверной части')]),
      ('Ж','Модели данных',[
        ('data-conceptual','Концептуальная модель данных'),
        ('data-er','Модель «сущность–связь»'),
        ('data-logical','Логическая модель данных'),
        ('ФизическаяБд','Физическая модель данных')]),
      ('И','Процессы и последовательности взаимодействия',[
        ('tobe-auth','Процесс предоставления доступа пользователю'),
        ('seq-auth','Последовательность регистрации и входа'),
        ('tobe-generate','Процесс генерации персонализированного рецепта'),
        ('seq-generate','Последовательность генерации рецепта'),
        ('seq-admin','Последовательность административных операций'),
        ('dfd-generate','Потоки данных при генерации рецепта'),
        ('seq-history-diet','Рацион, редактирование и оценка рецепта'),
        ('tobe-restrictions','Процесс управления запретами и аллергенами')])]
    lookup={}
    for letter,title,items in groups:
        for i,(key,caption) in enumerate(items,1):
            f=images/(key+'.png');assert f.exists(),f
            lookup[key]={'file':f,'ref':f'{letter}.{i}','caption':caption,'appendix':letter}
    return groups,lookup

def schema_from_source(repo):
    f=next((repo/'Optimization-Methods/laba_2/diagrams/Bd').glob('*.json'))
    source=json.loads(f.read_text(encoding='utf-8-sig'))
    by_id={t['id']:t for t in source['tables']}
    field_by_id={field['id']:field for t in source['tables'] for field in t['fields']}
    fk={r['startFieldId']:(by_id[r['endTableId']]['name']+'.'+field_by_id[r['endFieldId']]['name'],r['deleteConstraint']) for r in source['relationships']}
    groups=[['users','fitness_goals'],['user_profiles','parameter_history','ingredient_categories'],
            ['allergens','ingredient_allergens','ingredient_components','ingredients'],
            ['available_ingredients','user_restrictions','generation_requests'],
            ['recipes','recipe_ingredients'],['recipe_ratings','nutrition_reports','audit_log']]
    by_name={t['name']:t for t in source['tables']}
    models=[]
    for names in groups:
        for name in names:
            t=by_name[name];rows=[]
            for c in t['fields']:
                typ=c['type'].lower()+('('+c['size']+')' if c.get('size') else '')
                keys=[]
                if c.get('primary'):keys.append('PK')
                if c['id'] in fk:keys.append('FK → '+fk[c['id']][0])
                if c.get('unique'):keys.append('UNIQUE')
                rows.append([c['name'],typ,'Нет' if c.get('notNull') else 'Да','; '.join(keys) or '—'])
            models.append((name,rows))
    assert len(models)==17 and sum(len(rows) for _,rows in models)==143
    assert len(source['relationships'])==25
    return source,models,groups
