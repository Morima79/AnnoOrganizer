"""Account metadata must not be interpreted as Anno 1800 save archives."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class AccountSaveScanTests(unittest.TestCase):
    def test_nested_account_metadata_is_excluded_from_accounts_and_archive_roots(self):
        spec = importlib.util.spec_from_file_location('account_scan_fixture', ROOT / 'anno1800/tools/analyze_saves.py')
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(ROOT / 'anno1800/tools'), *sys.path]):
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module.ACCOUNT, module.ARCHIVE = root / 'accounts', root / 'archive'
            files = ['accounts/accountdata.a7s', 'accounts/profile/accountdata-PC.a7s',
                     'accounts/profile/AutoSave01.a7s', 'archive/profile/ACCOUNTDATA.a7s']
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            def fields(part):
                return {'setup': [(('GameSetupManager', 'GameSeed'), 123)],
                        'meta': [(('LastModTime',), 123456)],
                        'header': [(('CorporationProfile', 'ID'), 11),
                                   (('CorporationProfile', 'CorporationTime'), 1000)]}[part]
            with patch.object(module, 'members', return_value={
                    'gamesetup.a7s': 'setup', 'meta.a7s': 'meta', 'header.a7s': 'header'}) as members, \
                    patch.object(module, 'fields', side_effect=fields), \
                    patch.object(module, 'val', side_effect=lambda value: value):
                rows = module.scan(root / 'no-cache.json')
            self.assertEqual(len(rows), 1)
            self.assertEqual(Path(rows[0]['path']), Path('profile/AutoSave01.a7s'))
            members.assert_called_once()
            self.assertEqual(members.call_args.args[0].name, 'AutoSave01.a7s')


if __name__ == '__main__':
    unittest.main()
