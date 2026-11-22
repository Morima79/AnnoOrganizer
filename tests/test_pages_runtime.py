"""Include the Pages Node compatibility tests when Node 24 is available."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PagesRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for Pages runtime tests')
    def test_pages_preload_without_deployment_credentials(self):
        version = subprocess.check_output(['node', '--version'], text=True).strip()
        if int(version.lstrip('v').split('.')[0]) < 24:
            self.skipTest('Pages runtime tests require Node.js 24 or newer')
        result = subprocess.run(['node', '--test', str(ROOT / 'tests/pages_runtime.cjs')],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
