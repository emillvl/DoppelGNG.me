from pathlib import Path
import tempfile
import unittest

from PIL import Image

from doppelgng.validation import visual_diff


class VisualTests(unittest.TestCase):
    def test_detects_changed_layout_and_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            a, b = directory / 'a.png', directory / 'b.png'
            Image.new('RGB', (100, 80), 'white').save(a)
            Image.new('RGB', (100, 80), 'black').save(b)
            result = visual_diff(a, b, directory / 'difference.png')
            self.assertFalse(result['passed'])
            self.assertEqual(result['changed_pixel_ratio'], 1)
            Image.new('RGB', (99, 80), 'white').save(b)
            self.assertFalse(visual_diff(a, b, directory / 'difference.png')['passed'])

    def test_identical_images_pass_and_small_noise_is_measured(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            a, b = directory / 'a.png', directory / 'b.png'
            Image.new('RGB', (100, 80), (100, 100, 100)).save(a)
            Image.new('RGB', (100, 80), (103, 103, 103)).save(b)
            result = visual_diff(a, b, directory / 'difference.png')
            self.assertTrue(result['passed'])
            self.assertEqual(result['changed_pixel_ratio'], 0)
            self.assertEqual(result['mean_channel_difference'], 3)
