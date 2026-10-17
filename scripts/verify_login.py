"""Exercise login capture using owned HTTP fixtures and generated test secrets."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

import requests
from fixture_auth_site import login_site
from doppelgng.authentication import LoginError, LoginSession
from doppelgng.browser import Waterfox
from doppelgng.__main__ import main
from doppelgng.pipeline import Preview
from doppelgng.storage import Store, atomic_json, digest


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def main_check():
    scratch = Path(tempfile.mkdtemp(prefix='login-verification-', dir=ROOT / '.tools'))
    pointer = ROOT / '.doppelgng/current.json'
    previous = json.loads(pointer.read_text()) if pointer.exists() else None
    capture, exported = scratch / 'capture', scratch / 'export'
    results = {'profile_files_scanned': 0, 'profile_files_locked': 0, 'secret_matches': 0}
    locked_names = set()
    original_close = Waterfox.close
    try:
        with login_site() as (target, state), login_site() as (other, foreign):
            sensitive = [state[key].encode() for key in ('username', 'password', 'cookie', 'csrf', 'rotated')]

            def check_files(directory):
                checked = 0
                for file in directory.rglob('*'):
                    if file.is_file():
                        try:
                            body = file.read_bytes()
                        except PermissionError:
                            results['profile_files_locked'] += 1
                            locked_names.add(file.name)
                            continue
                        assert all(value not in body for value in sensitive), 'Known login data found in a file'
                        checked += 1
                return checked

            def close(browser):
                profile = Path(browser.driver.capabilities['moz:profile'])
                try:
                    results['profile_files_scanned'] += check_files(profile)
                finally:
                    original_close(browser)
                assert not profile.exists(), 'Temporary browser profile survived shutdown'

            def prompt(label):
                return state['username'] if 'username' in label else state['password']

            with patch('getpass.getpass', side_effect=prompt), patch.object(Waterfox, 'close', close):
                print('Checking protected capture at default desktop/mobile viewports.', flush=True)
                assert main(['capture', '--url', target, '--authorized', '--login', '--login-check', '#signed-in', '--output', str(capture), '--port', str(free_port())]) == 0
                manifest = Store(capture).data
                observations = [item for page in manifest['pages'].values() for item in page.get('validation', {}).get('observations', [])]
                results.update(pages=len(manifest['pages']), resources=len(manifest['resources']), visual_comparisons=len(observations), max_changed_pixel_ratio=max(item['visual']['changed_pixel_ratio'] for item in observations), navigation_checks=len(manifest['integration']['links']))
                results['capture_files_scanned'] = check_files(capture)
                print('Checking fresh login for standalone validation and export.', flush=True)
                assert main(['validate', '--output', str(capture), '--port', str(free_port()), '--login', '--login-check', '#signed-in']) == 0
                assert main(['export', '--output', str(capture), '--destination', str(exported)]) == 0
                results['export_files_scanned'] = check_files(exported)

                print('Checking response-cookie interception, origin scope, expiry, and blocked browser POST.', flush=True)
                login = LoginSession(target, check='#signed-in')
                try:
                    login.authenticate(lambda: (state['username'], state['password']))
                    with Waterfox(scratch / 'negative-browser', authentication=login) as browser:
                        browser.navigate(target + 'rotate')
                        assert browser.driver.get_cookies() == []
                        assert 'rotated=' in login.cookie_header(target)
                        foreign['cookie'] = state['cookie']
                        browser.driver.execute_async_script('const done=arguments[arguments.length-1];fetch(arguments[0],{mode:"no-cors",credentials:"include"}).then(()=>done(true),()=>done(false));', other)
                        assert foreign['cookie_headers'] == 0
                        state['expired'] = True
                        try:
                            browser.navigate(target)
                        except LoginError:
                            results['expired_session_rejected'] = True
                        else:
                            raise AssertionError('Expired login was accepted')
                        state['expired'] = False
                        browser.navigate(target)
                        before = state['posts']
                        browser.driver.execute_async_script('const done=arguments[arguments.length-1];fetch("/login",{method:"POST",body:"probe"}).then(()=>done(true),()=>done(false));')
                        assert state['posts'] == before
                        assert browser.bidi.failure is not None
                        results.update(browser_cookie_jar_empty=True, cross_origin_cookie_headers=foreign['cookie_headers'], browser_post_blocked=True)
                finally:
                    login.close()
                assert not login.cookies and not login.guard.patterns

                print('Checking hidden signed-in marker and capture failure checkpoint.', flush=True)
                state['hidden_marker'] = True
                failed = scratch / 'hidden-marker'
                try:
                    main(['capture', '--url', target, '--authorized', '--login', '--login-check', '#signed-in', '--output', str(failed), '--port', str(free_port())])
                except LoginError:
                    pass
                else:
                    raise AssertionError('Hidden signed-in marker was accepted')
                assert Store(failed).data['status'] == 'incomplete'
                assert not Store(failed).data['resources']
                check_files(failed)
                results['hidden_marker_rejected'] = True
                state['hidden_marker'] = False
                results['protected_native_heads'] = state['protected_heads']

        print('Checking exported replay with the original servers stopped and no login session.', flush=True)
        store = Store(exported)
        with Preview(store, free_port()) as preview, Waterfox(scratch / 'offline-browser') as browser:
            browser.navigate(preview.origin + '/')
            assert browser.driver.title == 'Private archive'
            for record in store.data['resources'].values():
                response = requests.get(preview.origin + record['public_url'], timeout=10)
                assert response.status_code == 200 and digest(response.content) == record['local_sha256']
            events = browser.bidi.events
            assert all(event.get('params', {}).get('request', {}).get('url', preview.origin).startswith(preview.origin) for event in events if event.get('method') == 'network.beforeRequestSent')
        results.update(capture='complete', validation='complete', export='complete', replay_without_login=True)
        results['profile_locked_names'] = sorted(locked_names)
        (scratch / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2), flush=True)
        print(f'Local verification evidence: {scratch}', flush=True)
    finally:
        if pointer.exists() and Path(json.loads(pointer.read_text())['manifest']).is_relative_to(scratch):
            if previous is None:
                pointer.unlink()
            else:
                atomic_json(pointer, previous)


if __name__ == '__main__':
    main_check()
