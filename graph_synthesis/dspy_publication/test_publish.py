"""Publication integrity checks on synthetic files, not benchmark evidence."""
import tempfile
import unittest
from pathlib import Path
from .publish import verify_package,sha,write

class PublicationTests(unittest.TestCase):
    def test_empty_package_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write(root/'package-manifest.json',{'sha256':{}})
            with self.assertRaises(ValueError):verify_package(root)
    def test_modified_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'part.json').write_text('{}')
            write(root/'package-manifest.json',{'sha256':{'part.json':sha(root/'part.json')}})
            (root/'part.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'hash/path mismatch'):verify_package(root)
    def test_partial_report_does_not_publish(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'part.json').write_text('{}')
            write(root/'package-manifest.json',{'sha256':{'part.json':sha(root/'part.json')}})
            with self.assertRaisesRegex(ValueError,'Missing report'):verify_package(root)
    def test_secret_model_or_font_files_not_published(self):
        for name in ('credential.key','model.gguf','font.ttf'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/name).write_text('not real')
                write(root/'package-manifest.json',{'sha256':{name:sha(root/name)}})
                with self.assertRaisesRegex(ValueError,'Disallowed'):verify_package(root)
    def test_extra_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'part.json').write_text('{}')
            write(root/'package-manifest.json',{'sha256':{'part.json':sha(root/'part.json')}})
            (root/'extra.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'inventory mismatch'):verify_package(root)

if __name__=='__main__':unittest.main()
