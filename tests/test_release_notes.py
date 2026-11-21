"""Verify version selection and failure handling for release descriptions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_notes import extract_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_selects_only_the_requested_version(self):
        text = '# Changelog\n\n## [Unreleased]\nFuture\n\n## [v0.1.2] - 2026-11-21\n### English\nLogos restored.\n### Deutsch\nLogos wiederhergestellt.\n\n## [v0.1.1]\nPrevious release.\n'
        self.assertEqual(extract_release_notes(text, 'v0.1.2'),
                         '### English\nLogos restored.\n### Deutsch\nLogos wiederhergestellt.\n')

    def test_missing_empty_or_duplicate_entry_is_rejected(self):
        for text in ('## [v0.1.1]\nOld', '## [v0.1.2]\n\n## [v0.1.1]\nOld',
                     '## [v0.1.2]\nFirst\n## [v0.1.2]\nSecond'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                extract_release_notes(text, 'v0.1.2')

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_release_notes('## [main]\nNotes', 'main')

    def test_current_changelog_has_bilingual_release_notes(self):
        notes = extract_release_notes((ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), 'v0.1.2')
        self.assertIn('### English', notes)
        self.assertIn('### Deutsch', notes)
        self.assertIn('Logos', notes)
        self.assertNotIn('## [v0.1.1]', notes)


if __name__ == '__main__':
    unittest.main()
