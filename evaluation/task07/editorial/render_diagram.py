"""Local SVG compatibility render; no data or agent execution."""
from pathlib import Path
from xml.etree import ElementTree as ET
import fitz

folder = Path(__file__).resolve().parent
source = folder / 'схема-работы.svg'
target = folder / 'схема-работы-готово.svg'
tree = ET.fromstring(source.read_text(encoding='utf-8'))
for node in tree.iter():
    if node.tag.endswith('}text'):
        node.set('text-anchor', 'middle')
        node.set('font-family', 'Arial')
target.write_bytes(ET.tostring(tree, encoding='utf-8', xml_declaration=True))
document = fitz.open(stream=target.read_bytes(), filetype='svg')
document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(target.with_suffix('.png'))
print(target.with_suffix('.png').name)
