"""Readable course-only context and container diagrams; leaves DOCX untouched."""
from pathlib import Path
import subprocess
import shutil
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
ASSETS = BASE / 'assets'
DRAWIO = Path(r'C:\Users\abdul\AppData\Local\Programs\draw.io\draw.io.exe')


def graph(width=820, height=410):
    model = ET.Element('mxGraphModel', {
        'dx': str(width), 'dy': str(height), 'grid': '0', 'page': '0',
        'pageWidth': str(width), 'pageHeight': str(height),
        'background': '#ffffff', 'adaptiveColors': 'auto',
    })
    root = ET.SubElement(model, 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    return model, root


def box(root, ident, text, x, y, width, height, *, parent='1', kind='normal', bold=False):
    style = ('rounded=1;arcSize=10;whiteSpace=wrap;html=1;'
             'fillColor=#ffffff;strokeColor=#333333;strokeWidth=1.6;'
             'fontColor=#111111;fontFamily=Arial;fontSize=20;spacing=9;')
    if bold:
        style += 'fontStyle=1;'
    if kind == 'database':
        style += 'shape=cylinder3;boundedLbl=1;size=14;'
    if kind == 'container':
        style = ('swimlane;startSize=34;rounded=1;arcSize=8;html=1;'
                 'fillColor=#ffffff;swimlaneFillColor=#ffffff;'
                 'strokeColor=#666666;strokeWidth=1.5;'
                 'fontColor=#111111;fontFamily=Arial;fontSize=18;fontStyle=1;')
    cell = ET.SubElement(root, 'mxCell', id=ident, value=text, style=style,
                         vertex='1', parent=parent)
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(width),
                  height=str(height), **{'as': 'geometry'})


def edge(root, ident, source, target, text='', *, parent='1', dashed=False):
    style = ('edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;'
             'jettySize=auto;html=1;endArrow=block;endFill=1;'
             'strokeColor=#333333;strokeWidth=1.6;'
             'fontColor=#111111;fontFamily=Arial;fontSize=18;'
             'labelBackgroundColor=#ffffff;')
    if dashed:
        style += 'dashed=1;'
    cell = ET.SubElement(root, 'mxCell', id=ident, value=text, style=style,
                         edge='1', source=source, target=target, parent=parent)
    ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})


def write(name, model):
    path = ASSETS / (name + '.drawio')
    ET.ElementTree(model).write(path, encoding='utf-8', xml_declaration=True)
    if shutil.which('node'):
        repair = r'''const fs = require("fs");
const file = process.argv[1];
let xml = fs.readFileSync(file, "utf8");
const diagram = xml.match(/<mxfile[\s\S]*?<\/mxfile>|<mxGraphModel[\s\S]*?<\/mxGraphModel>/);
if (diagram && xml.trim() !== diagram[0]) xml = diagram[0];
xml = xml.replace(/="([^"]*)"/g, function(m, v) {
return "=\"" + v.replace(/</g, "&lt;").replace(/&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)/g, "&amp;") + "\"";
});
xml = xml.replace(/<mxCell id="([^"]+)" parent="\1"\s*\/>/g, "<mxCell id=\"$1\" parent=\"0\"/>");
fs.writeFileSync(file, xml);'''
        subprocess.run(['node', '-e', repair, str(path)], check=True)
    parsed = ET.parse(path).getroot()
    cells = parsed.findall('.//mxCell')
    ids = [cell.get('id') for cell in cells]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate mxCell id')
    if any(c.get('id') == c.get('parent') for c in cells):
        raise ValueError('Self-parented cell')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    output = path.with_suffix('.drawio.png')
    proc = subprocess.run(
        [str(DRAWIO), '-x', '-f', 'png', '-e', '-b', '12', '--width', '1640',
         '--disable-gpu', '-o', str(output), str(path)],
        startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True, timeout=120,
    )
    if proc.returncode or not output.is_file():
        raise RuntimeError(proc.stdout.decode(errors='replace') +
                           proc.stderr.decode(errors='replace'))
    print(path)
    print(output)


def main():
    model, root = graph(height=350)
    box(root, 'user', 'Пользователь', 20, 40, 190, 85)
    box(root, 'admin', 'Администратор', 20, 240, 190, 85)
    box(root, 'system', '<b>АС ГРСН</b><br>Подбор и учёт<br>питания', 310, 140, 210, 100)
    box(root, 'gigachat', '<b>GigaChat API</b><br>Предложение<br>рецепта', 620, 140, 190, 100)
    edge(root, 'user-system', 'user', 'system', 'Подбор')
    edge(root, 'admin-system', 'admin', 'system', 'НСИ')
    edge(root, 'system-gigachat', 'system', 'gigachat', 'Запрос')
    write('course-context', model)

    model, root = graph(height=410)
    box(root, 'browser', 'Браузер<br><b>React / JS</b>', 20, 80, 140, 90)
    box(root, 'nginx', '<b>Nginx</b>', 240, 80, 105, 90)
    box(root, 'backend', 'Сервер приложения', 375, 40, 225, 350, kind='container')
    box(root, 'fastapi', '<b>FastAPI</b><br>Правила и расчёт', 15, 40, 195, 90, parent='backend')
    box(root, 'local', '<b>LocalGenerator</b><br>Локальный подбор', 15, 250, 195, 80, parent='backend')
    box(root, 'database', '<b>PostgreSQL</b><br>Данные', 660, 80, 150, 90, kind='database')
    box(root, 'gigachat', '<b>GigaChat API</b><br>Внешний подбор', 660, 290, 150, 90)
    box(root, 'files', 'Файловое хранилище<br>Отчёты и копии БД', 20, 290, 285, 90)
    edge(root, 'browser-nginx', 'browser', 'nginx', 'Запрос')
    edge(root, 'nginx-api', 'nginx', 'fastapi')
    edge(root, 'api-db', 'fastapi', 'database')
    edge(root, 'api-gigachat', 'fastapi', 'gigachat')
    edge(root, 'api-local', 'fastapi', 'local', 'Резерв', parent='backend')
    edge(root, 'api-files', 'fastapi', 'files', 'Сохранение')
    write('course-container', model)


if __name__ == '__main__':
    main()
