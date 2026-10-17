"""Apply Windows LZX storage compression only to the verified private browser."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import subprocess

from .dependencies import hash_file


def _filesystem(directory):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumePathNameW.restype = wintypes.BOOL
    kernel.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    volume, name = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(256)
    if not kernel.GetVolumePathNameW(str(directory), volume, len(volume)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.GetVolumeInformationW(volume.value, None, 0, None, None, None, name, len(name)):
        raise ctypes.WinError(ctypes.get_last_error())
    return name.value


def _storage(files):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCompressedFileSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetCompressedFileSizeW.restype = wintypes.DWORD
    physical = 0
    for file in files:
        high = wintypes.DWORD()
        ctypes.set_last_error(0)
        low = kernel.GetCompressedFileSizeW(str(file), ctypes.byref(high))
        if low == 0xffffffff and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        physical += (high.value << 32) | low
    return {'logical_bytes': sum(file.stat().st_size for file in files), 'physical_bytes': physical, 'files': len(files)}


def compress_runtime(root):
    # Import here so bootstrap can call this after provisioning the manifest.
    from .bootstrap import verify_runtime

    root = Path(root).resolve()
    runtime = verify_runtime(root)
    if platform.system() != 'Windows':
        return {'status': 'skipped', 'reason': 'LZX requires Windows'}
    core = (root / '.tools/waterfox/core').resolve()
    files = [(root / '.tools' / name).resolve() for name in sorted(runtime['files']) if name.startswith('waterfox/core/')]
    if not core.is_relative_to(root / '.tools') or any(not file.is_relative_to(core) for file in files):
        raise RuntimeError('Compression must stay inside the private browser directory')
    filesystem = _filesystem(core)
    if filesystem.upper() != 'NTFS':
        print(f'Browser storage compression skipped: {filesystem} is not NTFS; the verified runtime remains usable.', flush=True)
        return {'status': 'skipped', 'reason': f'{filesystem} is not NTFS'}

    marker = root / '.tools/runtime-compression.json'
    identity = {'schema': 1, 'algorithm': 'LZX', 'manifest_sha256': hash_file(root / '.tools/runtime-manifest.json')}
    before = _storage(files)
    try:
        previous = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        previous = None
    if previous == {**identity, **before}:
        print(f'Reusing LZX browser storage ({before["physical_bytes"] / 1_000_000:.1f} MB on disk)', flush=True)
        return {'status': 'reused', **previous}

    print('Applying LZX to the private browser files', flush=True)
    compact = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/compact.exe'
    result = subprocess.run([str(compact), '/C', '/F', '/A', '/Q', '/EXE:LZX', *map(str, files)], capture_output=True, timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    # A failed or interrupted compression must never bypass integrity checks.
    verify_runtime(root)
    if result.returncode:
        detail = (result.stderr or result.stdout).decode(errors='replace').strip()
        raise RuntimeError(f'Browser LZX compression failed (exit {result.returncode}); runtime contents verified. {detail}')
    measured = {**identity, **_storage(files)}
    marker.write_text(json.dumps(measured, indent=2) + '\n', encoding='utf-8')
    print(f'LZX browser storage: {measured["physical_bytes"] / 1_000_000:.1f} MB on disk ({measured["logical_bytes"] / 1_000_000:.1f} MB logical)', flush=True)
    return {'status': 'compressed', **measured}
