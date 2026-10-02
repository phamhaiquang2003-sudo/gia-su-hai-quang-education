"""Check the static export has working project-relative routes and only demo data."""
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from scripts.build_pages import build, ROOT


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attributes):
        for key, value in attributes:
            if key in ('href', 'src', 'action') and value:
                self.urls.append(value)


class PagesExportTest(unittest.TestCase):
    def test_all_preview_pages_and_assets_resolve_under_project_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            build(output)
            pages = [output / 'index.html', *sorted((output / 'demo').glob('*.html'))]
            self.assertEqual(len(pages), 11)
            self.assertTrue((output / '.nojekyll').exists())
            for page in pages:
                html = page.read_text(encoding='utf-8')
                self.assertIn('DEMO GIAO DIỆN', html)
                self.assertIn('id="preview-config"', html)
                self.assertNotIn('{{', html)
                self.assertNotIn('{%', html)
                self.assertNotIn('/exam.js', html)
                parser = Links()
                parser.feed(html)
                for url in parser.urls:
                    if url.startswith(('https://', '#')):
                        continue
                    self.assertFalse(url.startswith('/'), (page.name, url))
                    resolved = (page.parent / url).resolve()
                    relative = resolved.relative_to(output.resolve())
                    target = ROOT / relative if relative.parts[0] == 'static' else resolved
                    self.assertTrue(target.is_file(), (page.name, url))
            self.assertFalse((output / 'data').exists())
            self.assertFalse((output / 'uploads').exists())
            self.assertFalse((output / 'questions').exists())


if __name__ == '__main__':
    unittest.main()
