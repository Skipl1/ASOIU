from pathlib import Path
from copy import deepcopy
import os,sys,hashlib,zipfile,json,re
from lxml import etree as E
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
import pymupdf
base=Path(__file__).resolve().parents[1];repo=base.parents[1]
manifest=json.loads((base/'_build/source-assets-manifest.json').read_text(encoding='utf-8'))
f=Path(manifest['output']);z=zipfile.ZipFile(f)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
root=E.fromstring(z.read('word/document.xml'))
rels={r.get('Id'):r.get('Target') for r in E.fromstring(z.read('word/_rels/document.xml.rels'))}
ids=root.xpath('//a:blip/@r:embed',namespaces=ns)
assert len(ids)==len(manifest['illustrations'])==30
for rid,item in zip(ids,manifest['illustrations']):
    data=z.read('word/'+rels[rid]);original=(repo/item['source']).read_bytes()
    assert data==original,('Changed illustration',item['ref'])
    assert hashlib.sha256(data).hexdigest()==item['sha256']
    if item['kind']=='original':
        assert item['source'].startswith('Optimization-Methods\\laba_2\\images\\')
    else:
        assert item['asset'] in {'as-is','use-cases'}
        assert item['kind']=='restored_authorized'
assert sum(i['kind']=='original' for i in manifest['illustrations'])==28
text='\n'.join(root.xpath('//w:t/text()',namespaces=ns))
assert not re.search(r'\bТЗ\b|\bТП\b|техническ[а-я]+\s+(задани|проект)[а-я]*|руководств[а-я]*\s+(пользовател|администратор)[а-я]*',text,re.I)
assert 'светлая нейтральная основа' not in text
assert set(re.findall(r'рисунк(?:е|ах|и|а)\s+([0-9]+)',text,re.I))=={'1','2'}
assert not re.search(r'mock-|logical-users|physical-recipes|service-classes|domain-classes',z.read('word/document.xml').decode('utf-8'))
assert 'Посетитель' not in (base/'assets/use-cases.drawio').read_text(encoding='utf-8')
assert 'посетител' not in text.lower()
assert 'Продолжение приложения' not in text
for item in manifest['illustrations']:
    assert 'Рисунок '+item['ref']+' – '+item['caption'] in text
    assert re.search(r'(?<![А-Яа-я])'+re.escape(item['ref'])+r'(?!\d)',text)
# Compare actual dictionary rows to the retained JSON model.
physical=json.loads(next((repo/'Optimization-Methods/laba_2/diagrams/Bd').glob('*.json')).read_text(encoding='utf-8-sig'))
expected={t['name']:{c['name']:c for c in t['fields']} for t in physical['tables']}
found={};body=root.find('w:body',ns)
for i,node in enumerate(body):
    if node.tag!=ns['w'].join(['{','}p']):continue
    value=''.join(node.xpath('.//w:t/text()',namespaces=ns))
    m=re.match(r'Таблица Г\.\d+ – (\w+)$',value)
    if not m:continue
    table=body[i+1];rows=[]
    for row in table.findall('w:tr',ns)[1:]:
        cells=[''.join(c.xpath('.//w:t/text()',namespaces=ns)) for c in row.findall('w:tc',ns)]
        rows.append(cells)
    name=m.group(1);found[name]={r[0]:r for r in rows}
    assert set(found[name])==set(expected[name]),name
    for cname,row in found[name].items():
        col=expected[name][cname]
        typ=col['type'].lower()+('('+col['size']+')' if col.get('size') else '')
        assert row[1]==typ and row[2]==('Нет' if col.get('notNull') else 'Да'),(name,cname,row)
assert len(found)==17 and sum(map(len,found.values()))==143
# Compare both approved forms including table structure and typography.
def front_xml(package):
    r=E.fromstring(package.read('word/document.xml'));result=[];sections=0
    for node in r.find('w:body',ns):
        clone=deepcopy(node)
        sects=clone.xpath('.//w:sectPr',namespaces=ns);sections+=len(sects)
        for sect in sects:
            for ref in list(sect):
                if ref.tag in ['{'+ns['w']+'}headerReference','{'+ns['w']+'}footerReference']:sect.remove(ref)
        E.cleanup_namespaces(clone)
        result.append(E.tostring(clone,method='c14n'))
        if sections==2:break
    return result
before=zipfile.ZipFile(Path(os.environ['TEMP'])/'codex-course-original-assets/before.docx')
assert front_xml(z)==front_xml(before),'Approved first two forms changed'
plan=json.loads((base/'_build/page-plan.json').read_text(encoding='utf-8'))
pdf=pymupdf.open(next(Path(sys.argv[1]).glob('*.pdf')))
assert len(pdf)==len(plan['pages'])
for title,level,page,bookmark in plan['headings']:
    shown=title[:12] if title.startswith('Приложение ') else title
    assert re.sub(r'\s','',shown) in re.sub(r'\s','',pdf[page-1].get_text()),(page,title)
for item in manifest['illustrations']:
    pg=pdf[item['page']-1]
    assert re.sub(r'\s','','Рисунок '+item['ref']+' – '+item['caption']) in re.sub(r'\s','',pg.get_text()),item['ref']
    assert len(pg.get_image_info())>=1,item['ref']
for n,p in enumerate(pdf):
    if n==0:continue
    assert any(b[4].strip()==str(n+1) and b[1]>p.rect.height*.85 for b in p.get_text('blocks')),(n+1,'footer')
source_hashes={'lab2 copy/Привалихин Дмитрий_лаба_1_тз.pdf':'c5efa74cb2062467c3344b05a0923dd7f362b967aaa488b4dfb623db8079b828','laba_2/Привалихин Дмитрий_лаба_2_тп.pdf':'77c92fafd18e7fa6083f6222160b8ead0396ad13f43be1741febf18900d2b941'}
for path,h in source_hashes.items():assert hashlib.sha256((repo/'Optimization-Methods'/path).read_bytes()).hexdigest()==h,path
# The appendix body contains only its one designation, captions, images,
# native tables and empty section-break paragraphs. No explanatory prose.
in_appendix=False;appendix_labels=[]
for node in body:
    if node.tag!='{'+ns['w']+'}p':continue
    value=''.join(node.xpath('.//w:t/text()',namespaces=ns))
    if re.fullmatch(r'Приложение [А-Я]',value):
        in_appendix=True;appendix_labels.append(value)
    if in_appendix and value:
        assert re.match(r'^(Приложение [А-Я]$|Рисунок [А-Я]\.\d+ – |Таблица [А-Я]\.\d+ – )',value),('Appendix prose',value)
assert len(appendix_labels)==len(set(appendix_labels))==8
# Every numbered equation is editable OMML. Source notation and actual
# structured fractions/scripts are checked, rather than a bitmap or a string.
equations=json.loads((base/'_build/equations-source-manifest.json').read_text(encoding='utf-8'))['equations']
numbered=[]
for paragraph in root.xpath('//w:body/w:p[m:oMath]',namespaces=ns):
    label=''.join(paragraph.xpath('./w:r/w:t/text()',namespaces=ns))
    m=re.fullmatch(r'\((\d+)\)',label)
    if m:numbered.append((int(m.group(1)),paragraph))
assert [n for n,_ in numbered]==list(range(1,27)),[n for n,_ in numbered]
assert len(equations)==26
assert len(root.xpath('//m:f',namespaces=ns))>=15
assert len(root.xpath('//m:limLow',namespaces=ns))>=7
math_text=''.join(root.xpath('//m:t/text()',namespaces=ns))
assert all(s in math_text for s in ['88.362','13.397','4.799','5.677','447.593','9.247','3.098','4.330','TDEE','target','meal','7700','Φ','percent'])
assert 'J(m)' not in math_text and 'sⱼ' not in text
for item in equations:
    pgtext=pdf[item['page']-1].get_text()
    assert '('+str(item['number'])+')' in pgtext,(item['number'],'formula moved off planned page')
print(json.dumps({'output':str(f),'pages':len(pdf),'original_images_verified':28,'restored_diagrams_verified':2,'source_equations_verified':len(equations),'appendices_without_prose':True,'appendix_designations_once':8,'source_tables':len(found),'source_columns':143,'source_relationships':len(physical['relationships']),'approved_front_pages_unchanged':True,'all_sources_unchanged':True,'all_headings_and_captions_on_planned_pages':True},ensure_ascii=False,indent=2))
