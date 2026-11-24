"""Check published demo cell formats and self-contained offline workbook packages."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_demo_workbooks', ROOT/'scripts/publish_demo_workbooks.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def cell_format(package, sheet, address):
    styles = ET.fromstring(package.read('xl/styles.xml'))
    custom = {int(n.get('numFmtId')): n.get('formatCode') for n in styles.findall('s:numFmts/s:numFmt', NS)}
    cell = ET.fromstring(package.read(f'xl/worksheets/sheet{sheet}.xml')).find(f'.//s:c[@r="{address}"]', NS)
    style = styles.find('s:cellXfs', NS)[int(cell.get('s', 0))]
    code = int(style.get('numFmtId'))
    return custom.get(code, {0: 'General', 1: '0', 3: '#,##0', 46: '[h]:mm:ss'}.get(code, str(code)))


class ExcelExportTests(unittest.TestCase):
    def test_integer_display_preserves_the_saved_fractional_value(self):
        spec = importlib.util.spec_from_file_location('excel_summary', ROOT/'templates/anno_save_summary.py')
        summary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(summary)
        with tempfile.TemporaryDirectory() as folder:
            workbook = Path(folder)/'fraction.xlsx'
            with xlsxwriter.Workbook(workbook) as book:
                summary.write_statistics_sheet(book, [{'profile': 'Demo', 'date': '24.11.2026 20:00:00',
                    'seed': 123456, 'source': 'Demo save', 'values': {'money': 12345.75}}])
            with ZipFile(workbook) as package:
                self.assertEqual(cell_format(package, 1, 'E2'), '#,##0')
                cell = ET.fromstring(package.read('xl/worksheets/sheet1.xml')).find('.//s:c[@r="E2"]/s:v', NS)
                self.assertEqual(float(cell.text), 12345.75)

    def test_demo_numeric_cells_use_integers_and_ungrouped_seeds(self):
        for game in publisher.GAMES:
            with self.subTest(game=game), ZipFile(ROOT/f'site/downloads/{game}-map-demo.xlsx') as package:
                self.assertEqual(cell_format(package, 1, 'C2'), '0')
                for cell in ('D2', 'G2', 'H2', 'I2', 'J2', 'L2'):
                    node = ET.fromstring(package.read('xl/worksheets/sheet1.xml')).find(f'.//s:c[@r="{cell}"]', NS)
                    if node.get('t') != 's':
                        self.assertEqual(cell_format(package, 1, cell), '#,##0', cell)
                row = 6 if game == 'anno1404' else 7
                self.assertEqual(cell_format(package, 2, f'A{row}'), '0')
                rank_row = 5 if game == 'anno1404' else 6
                self.assertEqual(cell_format(package, 3, f'C{rank_row}'), '#,##0')
                self.assertEqual(cell_format(package, 3, f'D{rank_row}'), '[h]:mm:ss')
                self.assertNotIn(b'#,##0.##', package.read('xl/styles.xml'))

    def test_offline_packages_contain_only_the_workbook_and_referenced_demo_images(self):
        for game in publisher.GAMES:
            workbook = ROOT/f'site/downloads/{game}-map-demo.xlsx'
            images = publisher.workbook_images(workbook)
            with self.subTest(game=game), ZipFile(workbook.with_suffix('.zip')) as package:
                self.assertIsNone(package.testzip())
                self.assertEqual(sorted(package.namelist()), sorted([workbook.name, *images]))
                self.assertEqual(package.read(workbook.name), workbook.read_bytes())
                self.assertTrue(all(package.read(image).startswith(b'\x89PNG\r\n\x1a\n') for image in images))

    def test_publisher_rejects_external_links_and_traversal(self):
        for target in ('../private.png', 'map-images/../../private.png',
                       'https://example.com/private.png', 'C:/private.png',
                       'map-images/%2e%2e/private.png'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                workbook = Path(folder)/'test.xlsx'
                with ZipFile(workbook, 'w') as package:
                    package.writestr('xl/worksheets/_rels/sheet1.xml.rels',
                                     f'<Relationships><Relationship TargetMode="External" Target="{target}"/></Relationships>')
                with self.assertRaises(ValueError):
                    publisher.workbook_images(workbook)


if __name__ == '__main__':
    unittest.main()
