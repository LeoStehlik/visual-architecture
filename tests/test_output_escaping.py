import importlib.util
import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("renderer", ROOT / "scripts/render_architecture.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.scripts = []
        self.in_script = False
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "script":
            self.in_script = True
            self.scripts.append("")
    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data

class EscapingTests(unittest.TestCase):
    payload = '\" onload=\"window.INJECTED=1 <script>window.INJECTED=1</script> & \' '
    def data(self):
        return {"title": self.payload, "summary": self.payload, "nodes": [{"id": self.payload, "label": self.payload, "kind": "service", "x": 120, "y": 160}], "edges": []}
    def assert_no_active_payload(self, html, scripts):
        parser = Parser()
        parser.feed(html)
        self.assertEqual(len(parser.scripts), scripts)
        for _, attrs in parser.tags:
            self.assertFalse(any(k.lower().startswith("on") for k in attrs))
        return parser
    def test_svg_attributes_round_trip_without_handlers(self):
        for svg in (renderer.render(self.data()), renderer.render_share_card(self.data(), "example.json")):
            tree = ET.fromstring(svg)
            self.assertEqual(tree.attrib["aria-label"], self.payload)
            for node in tree.iter():
                self.assertFalse(any(k.lower().startswith("on") for k in node.attrib))
                self.assertNotEqual(node.tag.split("}")[-1], "script")
        self.assert_no_active_payload(renderer.render_html(self.data(), renderer.render(self.data()), "example.json"), 0)
    def test_gallery_script_terminator_and_filename_are_data(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path("examples").mkdir()
                data = self.data()
                data["story"] = [{"title": "</ScRiPt><script>window.INJECTED=1</script>", "text": "x"}]
                Path('examples/quoted\" onmouseover=\"bad.json').write_text(json.dumps(data))
                renderer.handle_gallery(SimpleNamespace(output="index.html"))
                html = Path("index.html").read_text()
                parser = self.assert_no_active_payload(html, 1)
                script = parser.scripts[0]
                payload = script.split("const artifacts = ", 1)[1].split(";\n", 1)[0]
                self.assertEqual(json.loads(payload)[0]["title"], self.payload)
                self.assertNotIn("</script", script.lower())
            finally:
                os.chdir(original)
    def test_json_preserves_special_characters(self):
        value = {"text": "<>&\u2028\u2029"}
        encoded = renderer.script_json(value)
        self.assertEqual(json.loads(encoded), value)
        self.assertNotIn("<", encoded)

if __name__ == "__main__":
    unittest.main()
