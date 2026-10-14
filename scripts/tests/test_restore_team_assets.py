"""Exercise restoration without network access or changes to project assets."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SPEC = importlib.util.spec_from_file_location(
    'restore_team_assets', Path(__file__).resolve().parents[1] / 'restore_team_assets.py'
)
restore = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restore)


class RestoreAssetsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.member = b'example model source'
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('source/model.txt', self.member)
        self.archive = archive.getvalue()
        self.asset = {
            'url': 'https://github.com/yeniwu46-max/plex/releases/download/test/model.zip',
            'path': 'models/model.zip',
            'sha256': hashlib.sha256(self.archive).hexdigest(),
            'extract': [{
                'member': 'source/model.txt',
                'path': 'models/source/model.txt',
                'sha256': hashlib.sha256(self.member).hexdigest(),
            }],
        }
        self.manifest = self.root / 'manifest.json'
        self.write_manifest()
        self.patches = [patch.object(restore, 'ROOT', self.root),
                        patch.object(restore, 'MANIFEST', self.manifest)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def write_manifest(self):
        self.manifest.write_text(json.dumps({'assets': [self.asset]}), encoding='utf-8')

    def run_main(self, *args):
        with patch('sys.argv', ['restore_team_assets.py', *args]), contextlib.redirect_stdout(io.StringIO()):
            return restore.main()

    def test_download_extract_and_repeat_without_network(self):
        with patch.object(restore.urllib.request, 'urlopen', return_value=io.BytesIO(self.archive)) as network:
            self.assertEqual(self.run_main(), 0)
            network.assert_called_once_with(self.asset['url'], timeout=120)
        self.assertEqual((self.root / 'models/source/model.txt').read_bytes(), self.member)
        with patch.object(restore.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
            self.assertEqual(self.run_main(), 0)
            self.assertEqual(self.run_main('--check'), 0)

    def test_check_reports_missing_without_writing_or_network(self):
        with patch.object(restore.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
            self.assertEqual(self.run_main('--check'), 1)
        self.assertFalse((self.root / 'models').exists())

    def test_corrupt_download_is_not_installed(self):
        with patch.object(restore.urllib.request, 'urlopen', return_value=io.BytesIO(b'corrupt')):
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                self.run_main()
        self.assertFalse((self.root / self.asset['path']).exists())

    def test_preserves_locally_edited_file(self):
        destination = self.root / 'models/source/model.txt'
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b'teammate edits')
        with patch.object(restore.urllib.request, 'urlopen', return_value=io.BytesIO(self.archive)):
            with self.assertRaisesRegex(ValueError, 'Local file differs'):
                self.run_main()
        self.assertEqual(destination.read_bytes(), b'teammate edits')
        self.assertEqual(self.run_main('--check'), 1)

    def test_rejects_destination_outside_repository(self):
        self.asset['path'] = '../outside.zip'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Path escapes repository'):
            self.run_main()

    def test_rejects_unexpected_download_url(self):
        self.asset['url'] = 'https://example.com/model.zip'
        self.write_manifest()
        with patch.object(restore.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
            with self.assertRaisesRegex(ValueError, 'Unexpected asset host'):
                self.run_main()


if __name__ == '__main__':
    unittest.main()
