from contextlib import nullcontext, redirect_stderr
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from doppelgng.__main__ import build_parser, main


class CaptureOptionsTests(unittest.TestCase):
    def test_defaults_preserve_existing_crawl_behavior(self):
        args = build_parser().parse_args(['capture', '--url', 'https://example.test', '--authorized'])
        self.assertTrue(args.respect_robots)
        self.assertEqual(args.checkpoint_every, 1)
        self.assertFalse(args.quiet)

    def test_terminal_choices_reach_capture(self):
        cases = [
            (['--ignore-robots', '--checkpoint-every', '7', '-q'], False, 7, True),
            (['--respect-robots', '--checkpoint-every', '0', '--quiet'], True, 0, True),
            ([], True, 1, False),
        ]
        for flags, robots, interval, quiet in cases:
            with self.subTest(flags=flags), patch('doppelgng.__main__.capture', return_value=SimpleNamespace(data={'status': 'complete'})) as capture, patch('doppelgng.__main__.workspace_lock', return_value=nullcontext()):
                result = main(['capture', '--url', 'https://example.test', '--authorized', *flags])
                self.assertEqual(result, 0)
                self.assertEqual(capture.call_args.args[2], 'example.test')
                self.assertEqual(capture.call_args.kwargs['respect_robots'], robots)
                self.assertEqual(capture.call_args.kwargs['checkpoint_every'], interval)
                self.assertEqual(capture.call_args.kwargs['quiet'], quiet)

    def test_invalid_checkpoint_values_fail_before_starting_a_capture(self):
        for value in ('-1', '1.5', 'abc'):
            with self.subTest(value=value), redirect_stderr(io.StringIO()) as errors, patch('doppelgng.__main__.capture') as capture:
                with self.assertRaises(SystemExit) as error:
                    main(['capture', '--url', 'https://example.test', '--authorized', '--checkpoint-every', value])
                self.assertEqual(error.exception.code, 2)
                self.assertIn('non-negative integer', errors.getvalue())
                capture.assert_not_called()

    def test_conflicting_robots_choices_are_rejected(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                build_parser().parse_args(['capture', '--url', 'https://example.test', '--ignore-robots', '--respect-robots'])
        self.assertEqual(error.exception.code, 2)

    def test_quiet_does_not_hide_command_errors(self):
        with redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit) as error:
                main(['capture', '--url', 'https://example.test', '-q'])
        self.assertEqual(error.exception.code, 2)
        self.assertIn('--authorized is required', errors.getvalue())
