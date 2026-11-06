from pathlib import Path
import sys,os
sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-pdf-review-deps'))
import pymupdf
base=Path(__file__).resolve().parents[3]
for rel,terms in [('Optimization-Methods/lab2 copy/Привалихин Дмитрий_лаба_1_тз.pdf',['4.7.2']),('Optimization-Methods/laba_2/Привалихин Дмитрий_лаба_2_тп.pdf',['generation_status'])]:
    d=pymupdf.open(base/rel)
    print(rel,len(d),repr(d[5].get_text()[:150]),flush=True)
    pg=d[18 if 'тз.pdf' in rel else 70]
    for b in pg.get_text('blocks'):
        print(tuple(round(v,1) for v in b[:4]),repr(b[4][:650]),flush=True)
    name='doc-tz-excerpt' if 'тз.pdf' in rel else 'doc-tp-excerpt'
    clip=pymupdf.Rect(83,37,575,248 if 'тз.pdf' in rel else 139)
    pg.get_pixmap(matrix=pymupdf.Matrix(3,3),clip=clip,alpha=False).save(base/'cursach/zapiska/assets'/(name+'.png'))
