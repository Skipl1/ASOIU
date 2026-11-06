from pathlib import Path
from docx import Document
from lxml import etree as E
import json,os
f=next(Path('cursach/dop_file').glob('Правила оформления КР*'))
d=Document(f); b=d.element.body
for i,e in enumerate(b):
    if i>43:break
    s=e.xpath('.//w:sectPr');br=e.xpath('.//w:br')
    print(i,e.tag.split('}')[-1], 'section='+str(bool(s)), 'breaks='+str([x.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type') for x in br]))
    if s:print(E.tostring(s[0],encoding='unicode'))
for i in [0,1,3,5,7,12,17,19,26,35,36,39,40,41,42]:
    print('\nELEMENT',i)
    if b[i].tag.endswith('tbl'):
        from docx.table import Table
        t=Table(b[i],d)
        for j,r in enumerate(t.rows):
            print('row',j,[(c.text,c.width.twips if c.width else None) for c in r.cells])
    else:print(E.tostring(b[i],encoding='unicode')[-3000:])
out=Path(os.environ['TEMP'])/'codex-coursework'/'reference-frontmatter.xml'
out.write_text('\n'.join(E.tostring(e,encoding='unicode') for e in list(b)[:43]),encoding='utf-8')
print('XML saved',out)
