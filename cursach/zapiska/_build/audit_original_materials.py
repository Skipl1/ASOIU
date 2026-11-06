from pathlib import Path
import sys,os,json,hashlib
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
from PIL import Image,ImageDraw,ImageFont
import pymupdf
root=Path(__file__).resolve().parents[3]
tmp=Path(os.environ['TEMP'])/'codex-course-original-assets';tmp.mkdir(exist_ok=True)
for folder in ['lab2 copy','laba_2']:
    files=[p for p in (root/'Optimization-Methods'/folder).glob('*.pdf') if 'Привалихин' in p.name]
    assert len(files)==1
    f=files[0];d=pymupdf.open(f)
    (tmp/(folder+'-text.txt')).write_text('\n\n'.join(p.get_text() for p in d),encoding='utf-8')
    print('PDF',f.name,'pages',len(d),'sha256',hashlib.sha256(f.read_bytes()).hexdigest())
imgs=root/'Optimization-Methods/laba_2/images'
names=['ui-login','ui-register','ui-profile','ui-profile-history','ui-restrictions','ui-ingredients','ui-generate-form','ui-generate-result','ui-history','ui-reports','ui-analysis','ui-admin','ui-structure','seq-auth','seq-admin','seq-generate','seq-history-diet','tobe-auth','tobe-generate','dfd-generate','c4-context','c4-container','c4-component','data-conceptual','data-er','data-logical','ФизическаяБд']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for start in range(0,len(names),9):
    canvas=Image.new('RGB',(1800,1275),'#dddddd');dr=ImageDraw.Draw(canvas)
    for j,n in enumerate(names[start:start+9]):
        f=imgs/(n+'.png');im=Image.open(f).convert('RGB');print(n,im.size)
        im.thumbnail((585,375));x=(j%3)*600;y=(j//3)*425
        canvas.paste(im,(x+(600-im.width)//2,y+34));dr.text((x+8,y+7),n,font=font,fill='black')
    canvas.save(tmp/f'contact-{start//9+1}.png')
db=json.loads(next((root/'Optimization-Methods/laba_2/diagrams/Bd').glob('*.json')).read_text(encoding='utf-8-sig'))
print('Physical source:',len(db['tables']),'tables',sum(len(t['fields']) for t in db['tables']),'columns',len(db['relationships']),'relationships')
