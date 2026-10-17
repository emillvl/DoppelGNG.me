import errno
import json
import os
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
import unittest
from unittest.mock import patch

import psutil

from doppelgng.storage import atomic_json, workspace_lock


class WorkspaceLockTests(unittest.TestCase):
    def test_failed_manifest_replacement_keeps_previous_checkpoint_and_removes_temporary_file(self):
        for error in (OSError(errno.ENOSPC, 'Controlled full disk'), PermissionError(errno.EACCES, 'Controlled denied write')):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / 'manifest.json'
                atomic_json(target, {'previous': 'verified'})
                with patch.object(Path, 'replace', side_effect=error):
                    with self.assertRaises(type(error)):
                        atomic_json(target, {'replacement': 'must not appear'})
                self.assertEqual(json.loads(target.read_text()), {'previous': 'verified'})
                self.assertEqual(list(Path(temporary).iterdir()), [target])

    def test_independent_atomic_writers_use_separate_temporary_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'current.json'
            ready = threading.Barrier(2)
            failures = []
            synchronized = set()
            synchronization_lock = threading.Lock()
            replace = Path.replace
            def synchronized_replace(source, destination):
                if destination == target:
                    with synchronization_lock:
                        first_attempt = threading.get_ident() not in synchronized
                        synchronized.add(threading.get_ident())
                    if first_attempt:
                        ready.wait(timeout=5)
                return replace(source, destination)
            def writer(value):
                try:
                    atomic_json(target, {'value': value})
                except BaseException as error:
                    failures.append(error)
            with patch.object(Path, 'replace', synchronized_replace):
                workers = [threading.Thread(target=writer, args=(value,)) for value in (1, 2)]
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join(timeout=8)
            self.assertFalse(any(worker.is_alive() for worker in workers))
            self.assertEqual(failures, [])
            self.assertIn(json.loads(target.read_text())['value'], (1, 2))
            self.assertEqual(list(Path(temporary).iterdir()), [target])

    def test_active_legacy_pid_lock_is_not_taken_over(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'capture.lock').write_text(json.dumps({'pid': os.getpid()}))
            with self.assertRaisesRegex(RuntimeError, 'Another capture'):
                with workspace_lock(temporary):
                    pass

    def test_two_stale_lock_contenders_cannot_both_own_the_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / 'capture.lock'
            lock.write_text(json.dumps({'pid': -1}))
            second_read = threading.Event()
            first_acquired = threading.Event()
            second_done = threading.Event()
            owners, failures = [], []
            real_pid_exists = psutil.pid_exists

            def pid_exists(pid):
                if pid != -1:
                    return real_pid_exists(pid)
                if threading.current_thread().name == 'first-contender':
                    second_read.wait(timeout=3)
                else:
                    second_read.set()
                    first_acquired.wait(timeout=3)
                return False

            def contender(name):
                try:
                    with workspace_lock(temporary):
                        owners.append(name)
                        if name == 'first':
                            first_acquired.set()
                            second_done.wait(timeout=4)
                except RuntimeError:
                    pass
                except BaseException as error:
                    failures.append(error)
                finally:
                    if name == 'second':
                        second_done.set()

            with patch('psutil.pid_exists', side_effect=pid_exists):
                first = threading.Thread(target=contender, args=('first',), name='first-contender')
                second = threading.Thread(target=contender, args=('second',), name='second-contender')
                first.start()
                second.start()
                first.join(timeout=8)
                second.join(timeout=8)
            self.assertFalse(first.is_alive() or second.is_alive())
            self.assertEqual(failures, [])
            self.assertEqual(len(owners), 1, owners)

    def test_corrupt_abandoned_lock_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'capture.lock').write_text('{truncated')
            with workspace_lock(temporary):
                self.assertTrue((Path(temporary) / 'capture.lock').is_file())

    def test_process_exit_releases_lock_without_deleting_its_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = 'import sys,time;from doppelgng.storage import workspace_lock\nwith workspace_lock(sys.argv[1]):\n print("locked",flush=True)\n time.sleep(30)\n'
            process = subprocess.Popen([sys.executable, '-c', source, temporary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), 'locked')
                with self.assertRaises(RuntimeError):
                    with workspace_lock(temporary):
                        pass
            finally:
                process.terminate()
                process.communicate(timeout=5)
            with workspace_lock(temporary):
                self.assertTrue((Path(temporary) / 'capture.lock').is_file())
