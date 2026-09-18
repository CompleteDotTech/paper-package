import tempfile
from pathlib import Path
import unittest
from graph_synthesis.render_current_paper import format_numeric_cells, validate_images


class RenderingTests(unittest.TestCase):
    def test_numeric_scores_counts_and_percentages_are_protected(self):
        for value in ('0.128923', '-7.26%', '66,048', '0', '.5', '+0.0310'):
            with self.subTest(value=value):
                self.assertIn('class="numeric"', format_numeric_cells('<td>'+value+'</td>'))

    def test_text_cell_is_not_forced_onto_one_line(self):
        text = '<td>Original independent-risk model</td>'
        self.assertEqual(format_numeric_cells(text), text)

    def test_formatting_is_idempotent(self):
        text = format_numeric_cells('<td style="text-align:right">0.128923</td>')
        self.assertEqual(format_numeric_cells(text), text)

    def test_local_image_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'plot.png').write_bytes(b'fixture')
            validate_images('![plot](plot.png)', root/'paper.md', root)

    def test_missing_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                validate_images('![plot](missing.png)', root/'paper.md', root)

    def test_remote_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                validate_images('![plot](https://example.com/plot.png)', root/'paper.md', root)

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'repository'
            root.mkdir()
            (root.parent/'outside.png').write_bytes(b'fixture')
            with self.assertRaises(ValueError):
                validate_images('![plot](../outside.png)', root/'paper.md', root)


if __name__ == '__main__':
    unittest.main()
