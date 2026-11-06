"""Editable Word equations transcribed from supplied lab2 copy/content.typ 4.6.

The source documents remain read-only. Equation identifiers, coefficients,
normalisation, bounds and the forecast horizon follow that supplied model.
"""
from copy import deepcopy

EQUATION_MANIFEST=[]

def mr(value,plain=False,size=14):
    r=OxmlElement('m:r')
    if plain:
        pr=OxmlElement('m:rPr');sty=OxmlElement('m:sty');sty.set(qn('m:val'),'p');pr.append(sty);r.append(pr)
    pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts')
    fonts.set(qn('w:ascii'),'Cambria Math');fonts.set(qn('w:hAnsi'),'Cambria Math');pr.append(fonts)
    sz=OxmlElement('w:sz');sz.set(qn('w:val'),str(2*size));pr.append(sz);r.append(pr)
    t=OxmlElement('m:t');t.text=str(value);t.set(qn('xml:space'),'preserve');r.append(t)
    return r

def content(parent,value):
    if isinstance(value,str):parent.append(mr(value))
    elif isinstance(value,(list,tuple)):
        for item in value:content(parent,item)
    else:parent.append(deepcopy(value))
    return parent

def sub(base,index):
    node=OxmlElement('m:sSub')
    content_element=OxmlElement('m:e');content(content_element,base);node.append(content_element)
    i=OxmlElement('m:sub');content(i,index);node.append(i);return node

def sup(base,index):
    if not isinstance(base,(str,list,tuple)) and base.tag==qn('m:sSub'):
        node=OxmlElement('m:sSubSup')
        node.append(deepcopy(base.find(qn('m:e'))));node.append(deepcopy(base.find(qn('m:sub'))))
        i=OxmlElement('m:sup');content(i,index);node.append(i);return node
    node=OxmlElement('m:sSup');e=OxmlElement('m:e');content(e,base);node.append(e)
    i=OxmlElement('m:sup');content(i,index);node.append(i);return node

def frac(num,den):
    node=OxmlElement('m:f');a=OxmlElement('m:num');content(a,num);node.append(a)
    b=OxmlElement('m:den');content(b,den);node.append(b);return node

def par(value):
    node=OxmlElement('m:d');pr=OxmlElement('m:dPr')
    for name,val in [('begChr','('),('endChr',')')]:
        c=OxmlElement('m:'+name);c.set(qn('m:val'),val);pr.append(c)
    node.append(pr);e=OxmlElement('m:e');content(e,value);node.append(e);return node

def summand(value,lower='i = 1',upper='n'):
    # Explicit native limits keep their positions in Word and in the local
    # review renderer, which otherwise changes n-ary limits to side scripts.
    operator=mr('∑',size=20)
    if upper is not None:
        hi=OxmlElement('m:limUpp');e=OxmlElement('m:e');e.append(operator);hi.append(e)
        lim=OxmlElement('m:lim');content(lim,upper);hi.append(lim);operator=hi
    lo=OxmlElement('m:limLow');e=OxmlElement('m:e');e.append(operator);lo.append(e)
    lim=OxmlElement('m:lim');content(lim,lower);lo.append(lim)
    return [lo,value]

def bar(value):
    node=OxmlElement('m:acc');pr=OxmlElement('m:accPr');c=OxmlElement('m:chr');c.set(qn('m:val'),'̄');pr.append(c);node.append(pr)
    e=OxmlElement('m:e');content(e,value);node.append(e);return node

def eq(parts,n,source):
    x=p('',indent=False,before=7,after=7)
    from docx.enum.text import WD_TAB_ALIGNMENT
    x.paragraph_format.tab_stops.add_tab_stop(Mm(85),WD_TAB_ALIGNMENT.CENTER)
    x.paragraph_format.tab_stops.add_tab_stop(Mm(170),WD_TAB_ALIGNMENT.RIGHT)
    x.add_run('\t');node=OxmlElement('m:oMath');content(node,parts);x._p.append(node)
    setfont(x.add_run('\t('+str(n)+')'))
    EQUATION_MANIFEST.append({'number':n,'source_expression':source,'page':PAGE})

def defs(items):
    for i,(symbols,description) in enumerate(items):
        paragraph=p('где ' if i==0 else '',indent=i==0)
        math=OxmlElement('m:oMath');content(math,symbols);paragraph._p.append(math)
        setfont(paragraph.add_run(' — '+description))

def total(letter):return sub(letter,mr('total',True))
def meal(letter):return sub(letter,mr('meal',True))
def xi(letter='x'):return sub(letter,'i')
def fact(letter):return sub(letter,mr('факт',True))
def goal(letter):return sub(letter,mr('цель',True))

page('Расчёт энергетической потребности')
smalltitle('Расчёт энергетической потребности')
text('''Для персонализации используются масса, рост, возраст, пол, активность и фитнес-ориентир. Расчётные правила задают ориентиры подбора питания. Базовый обмен для мужчин и женщин определяется формулами (1) и (2).''')
eq([sub(mr('BMR',True),'m'),' = 88.362 + 13.397 · m + 4.799 · h − 5.677 · a'],1,'BMR_m = 88.362 + 13.397*m + 4.799*h - 5.677*a')
eq([sub(mr('BMR',True),'f'),' = 447.593 + 9.247 · m + 3.098 · h − 4.330 · a'],2,'BMR_f = 447.593 + 9.247*m + 3.098*h - 4.330*a')
defs([([sub(mr('BMR',True),'m'),', ',sub(mr('BMR',True),'f')],'базовый обмен, ккал/сут;'),('m','масса тела, кг;'),('h','рост, см;'),('a','возраст, лет.')])
text('''Суточная потребность с учётом физической активности рассчитывается по формуле (3).''')
eq([mr('TDEE',True),' = ',mr('BMR',True),' · k'],3,'TDEE = BMR*k')
defs([('k','коэффициент физической активности: 1.2; 1.375; 1.55; 1.725; 1.9.')])
text('''Для выбранного фитнес-ориентира определяется суточная целевая потребность по формуле (4).''')
eq([sub('E',mr('target',True)),' = ',mr('TDEE',True),' + Δ'],4,'E_target = TDEE + Delta')
defs([('Δ','поправка, ккал/сут: −500 для снижения веса; 0 для поддержания формы; +300 для набора мышечной массы; +200 для повышения выносливости.')])
text('''Энергетическая цель одного приёма пищи определяется формулой (5).''')
eq([meal('E'),' = w · ',sub('E',mr('target',True))],5,'E_meal = w*E_target')
defs([('w ∈ (0; 1]','доля суточной нормы на один приём пищи; например, w = 1/3 при трёх приёмах пищи в день.')])
text('''Описание уровней активности приведено в таблице 15, поправки и целевые доли БЖУ для четырёх фитнес-ориентиров — в таблице 12. Расчётные показатели не являются индивидуальным медицинским назначением.''')

page('Расчёт пищевой ценности рецепта')
smalltitle('Расчёт пищевой ценности рецепта')
text('''Пищевая ценность рассчитывается по массе каждого ингредиента и справочным значениям на 100 г. Итоги белков, жиров, углеводов и энергии определяются формулами (6)–(9).''')
for num,letter in enumerate('PFCE',6):
    eq([total(letter),' = ',summand(frac([xi('m'),' · ',xi(letter)],'100'))],num,f'{letter}_total = sum_(i=1)^n (m_i*{letter}_i)/100')
defs([('n','количество ингредиентов;'),(xi('m'),'масса i-го ингредиента, г;'),([xi('P'),', ',xi('F'),', ',xi('C')],'белки, жиры и углеводы, г на 100 г;'),(xi('E'),'справочная энергетическая ценность, ккал на 100 г.')])
text('''Для определения долей БЖУ отдельно рассчитывается энергия по формуле Атуотера (10).''')
energy=sup(total('E'),mr('БЖУ',True))
eq([energy,' = 4 · ',total('P'),' + 9 · ',total('F'),' + 4 · ',total('C')],10,'E_total^БЖУ = 4*P_total + 9*F_total + 4*C_total')
text('''Коэффициенты 4, 9 и 4 ккал/г относятся к белкам, жирам и углеводам. Справочная энергия используется для калорийности рецепта и отчётов; энергия по БЖУ — для долей макронутриентов. Эти величины могут различаться из-за состава продукта и округления.''')
for num,letter,factor in [(11,'P',4),(12,'F',9),(13,'C',4)]:
    eq([sub(mr('percent',True),letter),' = ',frac([str(factor),' · ',total(letter)],energy),' · 100 %'],num,f'percent_{letter} = ({factor}*{letter}_total)/E_total^БЖУ*100%')
text('''При положительной энергии по БЖУ сумма трёх долей равна 100 %. Значения сопоставляются с целевыми долями выбранного фитнес-ориентира.''')

page('Целевые показатели приёма пищи')
smalltitle('Целевые показатели и проверка рецепта')
text('''Фитнес-ориентир задаёт целевые доли энергии от белков, жиров и углеводов. В расчёте доли используются как части единицы: например, 30 % соответствует 0.30; их сумма равна единице. Целевые массы нутриентов для приёма пищи определяются формулами (14)–(16).''')
for num,letter,factor in [(14,'P',4),(15,'F',9),(16,'C',4)]:
    eq([meal(letter),' = ',frac([meal('E'),' · ',sub('p',letter)],str(factor))],num,f'{letter}_meal = (E_meal*p_{letter})/{factor}')
defs([(meal('E'),'энергетическая цель приёма пищи, ккал;'),([sub('p','P'),', ',sub('p','F'),', ',sub('p','C')],'целевые доли энергии от белков, жиров и углеводов;'),([meal('P'),', ',meal('F'),', ',meal('C')],'целевые массы белков, жиров и углеводов, г.')])
text('''Отклонение калорийности готового рецепта от цели одного приёма пищи рассчитывается по формуле (17).''')
eq(['δ = ',total('E'),' − w · ',sub('E',mr('target',True))],17,'delta = E_total - w*E_target')
defs([('δ','отклонение, ккал;'),(sub('E',mr('target',True)),'суточная целевая потребность, ккал.')])
text('''Калорийность считается находящейся в диапазоне, если абсолютное отклонение, делённое на энергетическую цель приёма пищи, не превышает 10 %. При отклонении свыше 10 %, но не более 20 %, показывается предупреждение; свыше 20 % — выход за диапазон. Баланс БЖУ считается нормальным, если каждая фактическая доля отличается от целевой не более чем на 10 процентных пунктов.

Проверка калорийности не заменяет контроль запретов. Рецепт с запрещённым ингредиентом или компонентом не может считаться допустимым даже при точном совпадении энергии и БЖУ. В карточке результата должны различаться целевые значения, фактические итоги и причины несоответствия.''')

page('Подбор масс ингредиентов')
smalltitle('Подбор масс ингредиентов')
text('''После определения состава сервер подбирает массы x₁, …, xₙ, г. Целевой вектор b включает энергию, белки, жиры и углеводы одного приёма пищи. Используется задача взвешенных наименьших квадратов (18) с интервальными ограничениями (19).''')
inner=summand([sub('a','ki'),' ',xi()])
residual=frac([inner,' / 100 − ',sub('b','k')],sub('b','k'))
eq(['Φ(x) = ',summand([sub('λ','k'),' ',sup(par(residual),'2')],lower='k ∈ {E, P, F, C}',upper=None),' → ',mr('min',True)],18,'Phi(x) = sum_(k in {E,P,F,C}) lambda_k*((sum_(i=1)^n a_ki*x_i/100 - b_k)/b_k)^2 -> min')
eq([xi('l'),' ≤ ',xi(),' ≤ ',xi('u'),',   i = 1, …, n'],19,'l_i <= x_i <= u_i, i=1,...,n')
defs([(sub('a','ki'),'значение k-го показателя в i-м ингредиенте на 100 г;'),(sub('b','k'),'целевой показатель приёма пищи;'),([sub('λ','E'),' = 4; ',sub('λ','P'),' = 2; ',sub('λ','F'),' = ',sub('λ','C'),' = 1'],'веса критериев;'),(xi('u'),'минимум доступного количества и предельной массы в порции.')])
text('''Нижняя граница сохраняет присутствие выбранного ингредиента и определяется формулой (20).''')
eq([xi('l'),' = ',mr('min',True),par([mr('max',True),par(['5, 0.4 · ',sup(xi(),'0')]),', ',xi('u')])],20,'l_i = min(max(5,0.4*x_i^0),u_i)')
defs([(sup(xi(),'0'),'исходная масса ингредиента, предложенная моделью, г.')])
text('''Задача решается методом проекции градиента (21).''')
eq([sup('x',par('t + 1')),' = ',sub('Π','[l, u]'),par([sup('x','t'),' − ',frac('1','L'),' · ∇Φ',par(sup('x','t'))])],21,'x^(t+1) = Pi_[l,u](x^t - (1/L)*nabla Phi(x^t))')
defs([('Π','проекция каждой массы на её допустимый интервал;'),('L','оценка константы Липшица градиента; 1/L — шаг метода.')])
text('''Начальное приближение — середины интервалов. Остановка выполняется при малом изменении масс или после 2000 итераций; массы округляются до 5 г. Для резервного генератора предел составляет 1500 итераций. После округления заново проверяются ограничения и пищевая ценность.''')
text('''Если доля жиров ниже целевой более чем на 8 процентных пунктов и в составе нет продукта с долей энергии от жиров не менее 60 %, добавляется доступный источник жиров из набора пользователя. Его масса ограничивается интервалом от 0 до минимума доступного количества и 30 г.''')

page('Расчётная динамика массы тела')
smalltitle('Расчётная и фактическая динамика массы тела')
text('''Для аналитической оценки используется условный энергетический эквивалент 7700 ккал/кг. Расчётная масса по дням и прогноз на 30 дней определяются формулами (22) и (23).''')
eq([sub('m','d'),' = ',sub('m','d − 1'),' + ',frac([sub('E','d'),' − ',mr('TDEE',True)],'7700')],22,'m_d = m_(d-1) + (E_d - TDEE)/7700')
eq([sub('m','30'),' = ',sub('m',mr('end',True)),' + 30 · ',frac([bar('E'),' − ',mr('TDEE',True)],'7700')],23,'m_30 = m_end + 30*(E_bar - TDEE)/7700')
defs([(sub('m','0'),'последний известный замер на начало периода, а при его отсутствии — масса из профиля, кг;'),(sub('E','d'),'калорийность принятых в рацион рецептов за день d, ккал;'),(sub('m',mr('end',True)),'расчётная масса на конец периода, кг;'),(bar('E'),'средняя суточная калорийность по дням с данными, ккал.')])
text('''Дни без записей считаются нейтральными: расчётная масса не изменяется. Расчётный тренд строится при наличии рациона не менее чем за три дня. Фактический тренд использует последние замеры за каждый день при охвате не менее трёх дней. Скорость определяется наклоном прямой наименьших квадратов по формуле (24).''')
num=summand([par([sub('d','j'),' − ',bar('d')]),par([sub('m','j'),' − ',bar('m')])],lower='j',upper=None)
den=summand(sup(par([sub('d','j'),' − ',bar('d')]),'2'),lower='j',upper=None)
eq(['v = 7 · ',frac(num,den),' ',mr('кг/нед',True)],24,'v = 7*sum_j((d_j-d_bar)*(m_j-m_bar))/sum_j((d_j-d_bar)^2) кг/нед')
defs([(sub('d','j'),'номер дня замера;'),(sub('m','j'),'масса по замеру, кг;'),([bar('d'),', ',bar('m')],'средние значения дней и замеров.')])
text('''Для расчётной скорости используются точки расчётного тренда. Умножение на 7 переводит суточную скорость в кг/нед. Прогноз предполагает сохранение текущего рациона и активности; неполный учёт ограничивает его точность. Это оценка при заданных допущениях, а не обещание изменения массы.''')

page('Оценка соответствия рациона цели')
smalltitle('Оценка соответствия рациона цели')
text('''Анализ периода использует средние суточные энергию и БЖУ по дням, в которые есть принятые рецепты. Относительные отклонения от суточной цели рассчитываются формулой (25).''')
eq([sub('d','X'),' = ',frac([fact('X'),' − ',goal('X')],goal('X')),' · 100 %,   X ∈ {E, P, F, C}'],25,'d_X = (X_факт-X_цель)/X_цель*100%, X in {E,P,F,C}')
defs([(fact('X'),'средний суточный показатель за дни с данными;'),(goal('X'),'соответствующее суточное целевое значение.')])
text('''Абсолютное отклонение до 10 % отображается как норма, свыше 10 % до 20 % — как предупреждение, свыше 20 % — как значительное отклонение. Индекс соответствия цели рассчитывается по формуле (26).''')
eq(['S = ',mr('max',True),par(['0, 100 − ',par(['0.5 |',sub('d','E'),'| + 0.2 |',sub('d','P'),'| + 0.15 |',sub('d','F'),'| + 0.15 |',sub('d','C'),'|'])])],26,'S = max(0,100-(0.5*abs(d_E)+0.2*abs(d_P)+0.15*abs(d_F)+0.15*abs(d_C)))')
defs([('S','индекс от 0 до 100;'),([sub('d','E'),', ',sub('d','P'),', ',sub('d','F'),', ',sub('d','C')],'отклонения энергии и БЖУ, %.')])
text('''Рекомендации связываются с конкретными отклонениями: уменьшение или увеличение калорийности порций, уточнение белковых продуктов, корректировка углеводов и жиров, проверка несоответствующего цели тренда массы. При обнаружении рецепта, нарушающего текущие запреты, предлагается исключить его из рациона. При отсутствии данных предлагается сначала включить рецепты в рацион.

Индекс и тренды строятся по учтённым рецептам и замерам; они не подтверждают фактическое употребление всей пищи. В интерфейсе необходимо показывать период, число дней с записями и основания каждого вывода. Нулевая статистика при отсутствии записей не должна выдаваться за полноценную оценку питания.''')

(BASE/'_build/equations-source-manifest.json').write_text(json.dumps({'source':'Optimization-Methods/lab2 copy/content.typ','section':'4.6–4.6.4','equations':EQUATION_MANIFEST},ensure_ascii=False,indent=2),encoding='utf-8')
