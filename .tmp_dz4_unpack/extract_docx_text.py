from pathlib import Path
import re
xml_path = Path(r"d:/Для Windows 11/Всё подряд/Users/kreck/Desktop/Прочее/Дз по АСОИУ новый курс/Отчёты/.tmp_dz4_unpack/docx/word/document.xml")
xml = xml_path.read_text(encoding="utf-8", errors="ignore")
paras = []
for chunk in re.split(r"</w:p>", xml):
    ts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", chunk)
    if not ts:
        continue
    s = "".join(
        t.replace("&lt;", "<")
         .replace("&gt;", ">")
         .replace("&amp;", "&")
         .replace("&quot;", '"')
        for t in ts
    )
    if s.strip():
        paras.append(s)
text = "\n".join(paras)
out = Path(r"d:/Для Windows 11/Всё подряд/Users/kreck/Desktop/Прочее/Дз по АСОИУ новый курс/Отчёты/.tmp_dz4_unpack/dz4_docx_text.txt")
out.write_text(text, encoding="utf-8")
print(f"wrote {out} paras={len(paras)} chars={len(text)}")
