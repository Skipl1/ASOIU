"""Apply the requested appendix simplification and restore the two-actor diagram."""
from pathlib import Path
import ast,subprocess,re
from lxml import etree as E

base=Path(__file__).resolve().parent
part2=base/'part2.py'
value=part2.read_text(encoding='utf-8')
start=value.find("page('Правила расчёта пищевой ценности')")
if start>=0:
    stop=value.index("page('2.4 Технические требования')",start)
    value=value[:start]+"exec(compile(Path(__file__).with_name('source_equations.py').read_text(encoding='utf-8'),'source_equations.py','exec'),globals())\n\n"+value[stop:]
    part2.write_text(value,encoding='utf-8')

part=base/'part_end.py'
value=part.read_text(encoding='utf-8')
value=re.sub(r'^ +h\(title,structural=True,toc=False\)\n','',value,flags=re.M)
value=value.replace("    else:p('Продолжение приложения '+letter,align=WD_ALIGN_PARAGRAPH.CENTER,indent=False,bold=True,after=12)\n",'')
value=value.replace("        else:\n            p('Продолжение приложения '+letter,align=WD_ALIGN_PARAGRAPH.CENTER,indent=False,bold=True,after=12)\n",'')
value=value.replace("maxheight=(134 if i==0 else 147) if landscape else (213 if i==0 else 225)","maxheight=147 if landscape else 225")
# Remove only standalone prose from the appendix region; retain every table,
# its cells and caption, and all other narrative in the main text.
start=value.index("app('А','Материалы предпроектного анализа')")
stop=value.index('# Remove superseded source citations',start)
section=value[start:stop]
lines=section.splitlines(keepends=True)
deletions=[]
for node in ast.parse(section).body:
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='text':
        deletions.append((node.lineno-1,node.end_lineno))
for a,b in reversed(deletions):del lines[a:b]
value=value[:start]+''.join(lines)+value[stop:]
part.write_text(value,encoding='utf-8')

diagram=base.parent/'assets/use-cases.drawio'
tree=E.parse(str(diagram));root=tree.find('.//root')
cells={c.get('id'):c for c in root.findall('mxCell')}
if 'visitor' in cells:root.remove(cells['visitor'])
# All eight user cases share one column, so actor associations never cross
# other use-case ellipses. The original system boundary and admin stay intact.
cases=['register','login','profile','constraints','generate','history','rate','reports']
for i,name in enumerate(cases):
    geo=cells[name].find('mxGeometry');geo.set('x','35');geo.set('y',str(75+80*i))
    edge=cells['u_'+name];edge.set('source','user')
    edge.set('style','html=1;fontFamily=Arial;strokeColor=#000000;strokeWidth=1.5;edgeStyle=none;endArrow=none;exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
assert not any(c.get('value')=='Посетитель' for c in root.findall('mxCell'))
tree.write(str(diagram),encoding='UTF-8',xml_declaration=True,pretty_print=True)
exe=Path.home()/'AppData/Local/Programs/draw.io/draw.io.exe'
subprocess.run([str(exe),'--disable-gpu','--export','--format','png','--embed-diagram','--scale','2','--border','12','--output',str(diagram)+'.png',str(diagram)],check=True,creationflags=0x08000000,timeout=60)
print('Updated appendices, formula hook, and two-actor native diagram')
