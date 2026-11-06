from pathlib import Path
import os,sys,json,re
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
import pymupdf
from PIL import Image,ImageDraw,ImageFont
qa=Path(sys.argv[1])
pdf=next(qa.glob('*.pdf'));doc=pymupdf.open(pdf)
plan=json.loads((Path(__file__).with_name('page-plan.json')).read_text(encoding='utf-8'))
print('PDF pages',len(doc),'planned',len(plan['pages']))
findings=[]
for i,p in enumerate(doc):
    tx=p.get_text()
    boxes=p.get_text('blocks')
    content=[b for b in boxes if b[1]<775 and b[4].strip()]
    footers=[b[4].strip() for b in boxes if b[1]>(740 if i==1 else p.rect.height-70)]
    if i>0 and str(i+1) not in footers:findings.append((i+1,'footer',footers))
    if len(content)==0:findings.append((i+1,'blank',''))
    print(i+1,tx[:85].replace('\n',' | '), '...',len(tx),'chars',round(max((b[3] for b in content),default=0),1))
for t,l,pg,b in plan['headings']:
    shown=t[:12] if t.startswith('Приложение ') else t
    if pg<=len(doc) and re.sub(r'\s','',shown) not in re.sub(r'\s','',doc[pg-1].get_text()):findings.append((pg,'heading missing',t))
print('FINDINGS',findings)
(qa/'layout-summary.json').write_text(json.dumps({'actual_pages':len(doc),'planned_pages':len(plan['pages']),'findings':findings},ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
for start in range(0,len(doc),4):
    canvas=Image.new('RGB',(1664,1200*2),(210,210,210));dr=ImageDraw.Draw(canvas)
    for j in range(4):
        n=start+j
        if n>=len(doc):break
        im=Image.open(qa/f'page-{n+1}.png').convert('RGB');im.thumbnail((820,1160))
        x=(j%2)*832+(832-im.width)//2;y=(j//2)*1200+35
        canvas.paste(im,(x,y));dr.text(((j%2)*832+8,(j//2)*1200+5),str(n+1),font=font,fill='black')
    canvas.save(qa/f'contact-{start+1:02}.png')
