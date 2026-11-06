"""Retain the pre-revision body images byte for byte during this narrow edit."""
from pathlib import Path
import zipfile,os,hashlib
from lxml import etree as E
base=Path(__file__).resolve().parents[1]
before=Path(os.environ['TEMP'])/'codex-coursework-revision-20261107/before.docx'
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def images(path):
    z=zipfile.ZipFile(path)
    rels=E.fromstring(z.read('word/_rels/document.xml.rels'))
    targets={n.get('Id'):n.get('Target') for n in rels}
    doc=E.fromstring(z.read('word/document.xml'))
    return [z.read('word/'+targets[n]) for n in doc.xpath('//a:blip/@r:embed',namespaces=ns)]
original=images(before);current=images(base/'КП_Привалихин_Черновик (07.11.2026).docx')
assert len(original)==29 and len(current)==27,(len(original),len(current))
folder=base/'assets/body-before-revision';folder.mkdir(exist_ok=True)
changed=[]
for i,data in enumerate(original[:27],1):
    (folder/f'figure-{i:02}.png').write_bytes(data)
    if data!=current[i-1]:changed.append(i)
print('Restored figure numbers to baseline:',changed)
