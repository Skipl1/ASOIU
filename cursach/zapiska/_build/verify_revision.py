from pathlib import Path
import zipfile,hashlib,os,sys,re,json
from lxml import etree as E
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
import pymupdf
root=Path(__file__).resolve().parents[3]
out=root/'cursach/zapiska/КП_Привалихин_Черновик (07.11.2026).docx'
qa=Path(sys.argv[1]);pdf=pymupdf.open(next(qa.glob('*.pdf')))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
z=zipfile.ZipFile(out);xml=E.fromstring(z.read('word/document.xml'));styles=E.fromstring(z.read('word/styles.xml'))
texts=xml.xpath('//w:t/text()',namespaces=ns);visible='\n'.join(texts)
forbidden=re.findall(r'\bТЗ\b|\bТП\b|техническ[а-я]+\s+(?:задани|проект)[а-я]*|руководств[а-я]*\s+(?:пользовател|администратор)[а-я]*',visible,re.I)
assert not forbidden,forbidden
plan=json.loads(Path(__file__).with_name('page-plan.json').read_text(encoding='utf-8'))
assert len(pdf)==len(plan['pages'])==59
for title,level,page,bookmark in plan['headings']:
    assert re.sub(r'\s','',title) in re.sub(r'\s','',pdf[page-1].get_text()),(page,title)
    assert xml.xpath('//w:bookmarkStart[@w:name=$name]',name=bookmark,namespaces=ns)
for page in range(1,len(pdf)):
    blocks=pdf[page].get_text('blocks')
    assert any(b[4].strip()==str(page+1) and b[1]>740 for b in blocks),(page+1,'footer')
assert not re.search(r'^1$',pdf[0].get_text(),re.M)
topic='Предпроектное обследование объекта автоматизации и основные проектные решения для интеллектуальной системы генерации персонализированных рецептов спортивного питания'
for page in [0,1]:
    assert re.sub(r'\s','',topic) in re.sub(r'\s','',pdf[page].get_text()),('topic clipping',page+1)
refs=[int(v) for m in re.findall(r'\[([0-9; ]+)\]',visible) for v in re.findall(r'\d+',m)]
assert refs and min(refs)==1 and max(refs)==11
style_ids=set(styles.xpath('//w:style/@w:styleId',namespaces=ns))
assert len(style_ids)==len(styles.xpath('//w:style',namespaces=ns))
for value in xml.xpath('//w:pStyle/@w:val|//w:rStyle/@w:val|//w:tblStyle/@w:val',namespaces=ns):assert value in style_ids,value
ref=root/'cursach/dop_file/Правила оформления КР по проектированию АСОИУ_2026 + Темы КР.docx'
assert hashlib.sha256(ref.read_bytes()).hexdigest().upper()=='F67149603FC9571FC1AEA82778B9EB965E6E48774F0EF2EA62BF231221A72AA5'
before=zipfile.ZipFile(Path(os.environ['TEMP'])/'codex-coursework-revision-20261107/before.docx')
oldmedia={hashlib.sha256(before.read(n)).hexdigest() for n in before.namelist() if n.startswith('word/media/')}
newmedia={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
assert newmedia<=oldmedia, 'Unexpected changes in body figures'
print(json.dumps({'docx':str(out),'rendered_pages':len(pdf),'headings_checked':len(plan['headings']),'forbidden_mentions':forbidden,'source_references_range':[min(refs),max(refs)],'unchanged_figure_assets':len(newmedia),'removed_document_excerpt_assets':len(oldmedia-newmedia),'reference_unchanged':True},ensure_ascii=False,indent=2))
