"""Retain original chart XML and embedded workbooks during a slide-only edit."""
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET


def preserve(source, candidate):
    source, candidate = Path(source), Path(candidate)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(candidate) as edited:
        parts = {n: original.read(n) for n in original.namelist()
                 if n.startswith(('ppt/slides/charts/', 'ppt/embeddings/'))}
        charts = [n for n in parts if n.endswith('.xml') and '/_rels/' not in n]
        assert len(charts) == 3
        ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        for name in charts:
            # A slide-only edit must not change any cached quantitative evidence.
            old = ET.fromstring(parts[name])
            new = ET.fromstring(edited.read(name))
            values = lambda tree: [n.text for n in tree.findall('.//c:pt/c:v', ns)]
            assert values(old) == values(new), f'Chart data changed: {name}'
        contents = {n: edited.read(n) for n in edited.namelist()}
        contents.update(parts)
        namespace = 'http://schemas.openxmlformats.org/package/2006/content-types'
        ET.register_namespace('', namespace)
        types = ET.fromstring(contents['[Content_Types].xml'])
        source_types = ET.fromstring(original.read('[Content_Types].xml'))
        existing = {(n.tag, n.get('PartName'), n.get('Extension')) for n in types}
        for item in source_types:
            name = item.get('PartName', '').lstrip('/')
            if name in parts or item.get('Extension') == 'xlsx':
                key = (item.tag, item.get('PartName'), item.get('Extension'))
                if key not in existing:
                    types.append(item)
                    existing.add(key)
        contents['[Content_Types].xml'] = ET.tostring(types, encoding='utf-8', xml_declaration=True)
    temp = candidate.with_suffix('.chart-preserved.pptx')
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as result:
        for name, data in contents.items():
            result.writestr(name, data)
    temp.replace(candidate)
    with zipfile.ZipFile(candidate) as result:
        assert result.testzip() is None
        assert all(result.read(name) == data for name, data in parts.items())


if __name__ == '__main__':
    preserve(sys.argv[1], sys.argv[2])
