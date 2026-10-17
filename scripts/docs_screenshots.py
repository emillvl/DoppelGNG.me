"""Record an owned capture and render documentation images from its output."""
from __future__ import annotations

import html
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from fixture_site import Handler
from doppelgng.browser import Waterfox
from doppelgng.pipeline import Preview
from doppelgng.storage import Store, atomic_json


def available_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def command(arguments, log):
    invocation = ['node', 'scripts/python.mjs', '-m', 'doppelgng', *arguments]
    print(subprocess.list2cmdline(invocation), flush=True)
    with log.open('w', encoding='utf-8') as handle:
        result = subprocess.run(invocation, cwd=ROOT, text=True, stdout=handle, stderr=subprocess.STDOUT)
    output = log.read_text(encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}):\n{output}')
    return invocation, output


def transcript(invocation, output):
    normalized = output.replace(json.dumps(str(ROOT))[1:-1], '<workspace>')
    normalized = normalized.replace(str(ROOT), '<workspace>').replace(ROOT.as_posix(), '<workspace>')
    return '$ ' + subprocess.list2cmdline(invocation) + '\n\n' + normalized


def terminal_image(browser, scratch, assets, name, title, text):
    (assets / f'{name}.txt').write_text(text, encoding='utf-8')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<style>
*{box-sizing:border-box}html,body{margin:0;background:#11161c;color:#d7e0e8}
body{padding:32px;font:15px/1.65 Consolas,"Liberation Mono",monospace}
header{color:#96c5ad;border-bottom:1px solid #35414d;padding:0 0 16px;margin-bottom:20px}
pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}
</style><header>''' + html.escape(title) + '</header><pre>' + html.escape(text) + '</pre></html>'
    page = scratch / f'{name}.html'
    page.write_text(document, encoding='utf-8')
    browser.viewport(1440, 900)
    browser.navigate(page.as_uri())
    height = browser.driver.execute_script('return Math.ceil(document.body.getBoundingClientRect().height)')
    browser.viewport(1440, max(400, height))
    browser.driver.save_screenshot(str(assets / f'{name}.png'))


def main():
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='documentation-', dir=tools))
    assets = ROOT / 'docs/assets'
    assets.mkdir(parents=True, exist_ok=True)
    capture = scratch / 'capture'
    pointer = ROOT / '.doppelgng/current.json'
    previous = json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else None
    fixture = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    try:
        target = f'http://127.0.0.1:{fixture.server_port}'
        capture_command, capture_output = command([
            'capture', '--url', target, '--authorized', '--output', capture.relative_to(ROOT).as_posix(),
            '--port', str(available_port()), '--scenarios', 'tests/fixture-scenarios.json',
        ], scratch / 'capture.log')
        store = Store(capture)
        if store.data['status'] != 'complete':
            raise RuntimeError('The documentation fixture did not complete')
        status_command, status_output = command(['status', '--output', capture.relative_to(ROOT).as_posix()], scratch / 'status.log')
        command(['export', '--output', capture.relative_to(ROOT).as_posix(), '--destination', (scratch / 'export').relative_to(ROOT).as_posix()], scratch / 'export.log')
        with Preview(store, available_port()) as preview, Waterfox(scratch / 'browser') as browser:
            browser.viewport(1440, 900)
            browser.navigate(preview.origin + '/')
            browser.driver.save_screenshot(str(assets / 'fixture-replay-desktop.png'))
            terminal_image(browser, scratch, assets, 'terminal-capture', 'DoppelGNG.me / owned fixture capture', transcript(capture_command, capture_output))
            terminal_image(browser, scratch, assets, 'terminal-status', 'DoppelGNG.me / capture status', transcript(status_command, status_output))
        observations = [observation for page in store.data['pages'].values() for observation in page.get('validation', {}).get('observations', [])]
        record = {
            'target': target,
            'status': store.data['status'],
            'pages': len(store.data['pages']),
            'resources': len(store.data['resources']),
            'visual_comparisons': len(observations),
            'max_changed_pixel_ratio': max(item['visual']['changed_pixel_ratio'] for item in observations),
            'navigation_checks': len(store.data['integration']['links']),
            'transcript_note': 'Actual CLI output; workspace path replaced by <workspace>. Terminal panels rendered in Waterfox.',
        }
        (assets / 'fixture-evidence.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record, indent=2), flush=True)
        print(f'Local evidence: {scratch}', flush=True)
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=5)
        if pointer.exists() and Path(json.loads(pointer.read_text(encoding='utf-8'))['manifest']) == capture / 'manifest.json':
            if previous is None:
                pointer.unlink()
            else:
                atomic_json(pointer, previous)


if __name__ == '__main__':
    main()
