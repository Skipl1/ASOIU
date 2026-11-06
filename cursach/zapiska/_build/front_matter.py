"""Reuse the first two native reference forms; execute in the builder namespace."""
from copy import deepcopy
from hashlib import sha256
from docx.table import Table

reference_path=REPO/'cursach/dop_file/Правила оформления КР по проектированию АСОИУ_2026 + Темы КР.docx'
assert sha256(reference_path.read_bytes()).hexdigest().upper()=='F67149603FC9571FC1AEA82778B9EB965E6E48774F0EF2EA62BF231221A72AA5'
reference=Document(reference_path)
reference_elements=list(reference.element.body)
prefix='FrontRef_'
style_map={s.get(qn('w:styleId')):prefix+s.get(qn('w:styleId')) for s in reference.styles.element.findall(qn('w:style'))}
ref_normal=reference.styles['Normal'].style_id
number_map={}
abstract_map={}
src_number=reference.part.numbering_part.element
dst_number=D.part.numbering_part.element
for tag,mapping,attr in [('abstractNum',abstract_map,'abstractNumId'),('num',number_map,'numId')]:
    for node in src_number.findall(qn('w:'+tag)):
        mapping[node.get(qn('w:'+attr))]=str(1000+int(node.get(qn('w:'+attr))))

def remap_styles(node):
    for tag in ['pStyle','rStyle','tblStyle','basedOn','next','link','styleLink','numStyleLink']:
        for n in node.iter(qn('w:'+tag)):
            value=n.get(qn('w:val'))
            if value in style_map:n.set(qn('w:val'),style_map[value])
    for n in node.iter(qn('w:numId')):
        value=n.get(qn('w:val'))
        if value in number_map:n.set(qn('w:val'),number_map[value])
    return node

for src in reference.styles.element.findall(qn('w:style')):
    node=remap_styles(deepcopy(src))
    node.set(qn('w:styleId'),style_map[src.get(qn('w:styleId'))])
    node.attrib.pop(qn('w:default'),None)
    nm=node.find(qn('w:name'))
    if nm is not None:nm.set(qn('w:val'),'Reference '+nm.get(qn('w:val')))
    if src.get(qn('w:styleId'))==ref_normal:
        defaults=reference.styles.element.find(qn('w:docDefaults'))
        if defaults is not None:
            for parent_tag,child_tag in [('pPrDefault','pPr'),('rPrDefault','rPr')]:
                default=defaults.find(qn('w:'+parent_tag))
                default=default.find(qn('w:'+child_tag)) if default is not None else None
                if default is not None:
                    target=node.find(qn('w:'+child_tag))
                    if target is None:target=OxmlElement('w:'+child_tag);node.append(target)
                    for item in default:
                        if target.find(item.tag) is None:target.append(deepcopy(item))
        # Source defaults are empty (Word's single/zero). Make them explicit so
        # the target package's 8pt/1.08 docDefaults cannot change the form rhythm.
        props=node.find(qn('w:pPr'))
        if props is None:
            props=OxmlElement('w:pPr');rprops=node.find(qn('w:rPr'))
            node.insert(list(node).index(rprops) if rprops is not None else len(node),props)
        spacing=OxmlElement('w:spacing')
        for key,value in [('before','0'),('after','0'),('line','240'),('lineRule','auto')]:spacing.set(qn('w:'+key),value)
        props.append(spacing)
        ind=OxmlElement('w:ind');ind.set(qn('w:firstLine'),'0');props.append(ind)
        # Restore the canonical ordering of imported run properties.
        rprops=node.find(qn('w:rPr'))
        if rprops is not None:
            fonts=rprops.find(qn('w:rFonts'))
            if fonts is not None:rprops.remove(fonts);rprops.insert(0,fonts)
    D.styles.element.append(node)
for src in src_number:
    tag=src.tag.split('}')[-1]
    if tag not in ['abstractNum','num']:continue
    node=remap_styles(deepcopy(src));attr='abstractNumId' if tag=='abstractNum' else 'numId'
    node.set(qn('w:'+attr),(abstract_map if tag=='abstractNum' else number_map)[src.get(qn('w:'+attr))])
    for item in node.iter(qn('w:abstractNumId')):
        item.set(qn('w:val'),abstract_map[item.get(qn('w:val'))])
    dst_number.append(node)

def copy_geometry(section,source):
    for tag in ['pgSz','pgMar','cols','docGrid']:
        old=section._sectPr.find(qn('w:'+tag))
        if old is not None:section._sectPr.remove(old)
        item=source._sectPr.find(qn('w:'+tag))
        if item is not None:section._sectPr.append(deepcopy(item))
    order=['headerReference','footerReference','footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange']
    section._sectPr[:]=sorted(section._sectPr,key=lambda n:order.index(n.tag.split('}')[-1]) if n.tag.split('}')[-1] in order else 99)

def clean_clone(src):
    node=remap_styles(deepcopy(src))
    for para in node.iter(qn('w:p')):
        props=para.find(qn('w:pPr'))
        if props is None:props=OxmlElement('w:pPr');para.insert(0,props)
        if props.find(qn('w:pStyle')) is None:
            st=OxmlElement('w:pStyle');st.set(qn('w:val'),style_map[ref_normal]);props.insert(0,st)
    for tag in ['sectPr','pict','drawing','commentRangeStart','commentRangeEnd','commentReference','highlight','bookmarkStart','bookmarkEnd']:
        for item in list(node.iter(qn('w:'+tag))):
            if item.getparent() is not None:item.getparent().remove(item)
    for item in node.iter(qn('w:color')):
        if item.get(qn('w:val'),'').upper() in ['FF0000','C00000']:item.set(qn('w:val'),'000000')
    for hyperlink in node.iter(qn('w:hyperlink')):
        rel_id=hyperlink.get(qn('r:id'))
        if rel_id and rel_id in reference.part.rels:
            rel=reference.part.rels[rel_id]
            if rel.is_external:hyperlink.set(qn('r:id'),D.part.relate_to(rel.target_ref,rel.reltype,is_external=True))
    return node

def write_para(para,value,plain=False,size=None):
    rpr=next(iter(para.xpath('./w:r/w:rPr')),None)
    rpr=deepcopy(rpr) if rpr is not None else OxmlElement('w:rPr')
    if plain:
        for tag in ['i','iCs','color','highlight']:
            for n in list(rpr.iter(qn('w:'+tag))):n.getparent().remove(n)
    if size is not None:
        sz=rpr.find(qn('w:sz'))
        if sz is None:sz=OxmlElement('w:sz');rpr.append(sz)
        sz.set(qn('w:val'),str(size*2))
    for child in list(para):
        if child.tag!=qn('w:pPr'):para.remove(child)
    for i,line in enumerate(value.split('\n')):
        run=OxmlElement('w:r');run.append(deepcopy(rpr))
        if i:run.append(OxmlElement('w:br'))
        val=OxmlElement('w:t');val.set(qn('xml:space'),'preserve');val.text=line;run.append(val);para.append(run)

def write_cell(cell,value,plain=False):
    paragraphs=cell._tc.findall(qn('w:p'))
    write_para(paragraphs[0],value,plain)
    for extra in paragraphs[1:]:cell._tc.remove(extra)

def append_elements(elements):
    for node in elements:D.element.body.insert(len(D.element.body)-1,node)

title={i:clean_clone(reference_elements[i]) for i in range(27)}
tt=Table(title[12],D)
write_cell(tt.cell(0,0),'Предпроектное обследование объекта автоматизации\nи основные проектные решения для интеллектуальной')
write_cell(tt.cell(1,0),'системы генерации персонализированных рецептов\nспортивного питания')
for row in tt.rows:
    for height in row._tr.xpath('./w:trPr/w:trHeight'):
        height.set(qn('w:hRule'),'atLeast');height.set(qn('w:val'),'640')
code=Table(title[17],D)
write_cell(code.cell(1,1),'1.___.00.00 – ПЗ',True)
write_para(title[18],'обозначение документа',True,size=9)
props=title[18].find(qn('w:pPr'))
for key in ['rPr','pStyle']:
    node=props.find(qn('w:'+key))
    if node is not None:props.remove(node)
st=OxmlElement('w:pStyle');st.set(qn('w:val'),style_map[ref_normal]);props.insert(0,st)
for cap in list(title[18].iter(qn('w:caps'))):cap.getparent().remove(cap)
people=Table(title[19],D)
write_cell(people.cell(0,2),'ИСИб-23-1',True)
write_cell(people.cell(0,6),'Д.С. Привалихин',True)
write_cell(people.cell(2,6),'Р.Д. Гутгарц',True)
# The topic needs two more text lines than the example; reclaim two empty source lines.
title_elements=[e for i,e in title.items() if i not in [10,11]]
section=page('Титульный лист');copy_geometry(section,reference.sections[0]);append_elements(title_elements)

assignment={i:clean_clone(reference_elements[i]) for i in range(27,42)}
form=Table(assignment[35],D)
write_cell(form.cell(1,2),'Привалихину Д.С., группа ИСИб-23-1',True)
write_cell(form.cell(3,1),'Предпроектное обследование объекта',True)
write_cell(form.cell(4,0),'автоматизации и основные проектные решения для интеллектуальной системы генерации персонализированных рецептов спортивного питания',True)
write_cell(form.cell(8,0),'Предпроектное обследование процесса персонального планирования спортивного питания; сведения о параметрах пользователя, доступных продуктах, пищевых ограничениях и задачах учёта рациона (вариант № ___).',True)
rows=form._tbl.findall(qn('w:tr'))
form._tbl.remove(rows[5])
received=Table(assignment[39],D);write_cell(received.cell(0,3),'Д.С. Привалихин',True)
section=page('Задание');copy_geometry(section,reference.sections[1]);append_elements(assignment.values())
# Keep the source footer with number 2; the reference has no first-page suppression here.
section.different_first_page_header_footer=False
