import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from .pipeline import capture, Preview, navigation_validation
from .browser import Waterfox
from .storage import Store, workspace_lock
from .validation import local_validate, interaction_check
from .reconstruct import public_url
from .export import default_output, export_project
from .dependencies import default_crawler


def main():
    parser = argparse.ArgumentParser(description='Capture and reconstruct an authorized website using your existing crawler and headless Waterfox.')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('capture', help='Discover, extract, reconstruct, and validate every reachable in-scope page')
    run.add_argument('--url', required=True)
    run.add_argument('--authorized', action='store_true', help='Confirm you own this website or are authorized to reproduce it')
    run.add_argument('--crawler', default=str(default_crawler()), help='Optional crawler override; defaults to the pinned project-local crawler installed by npm run setup')
    run.add_argument('--output')
    run.add_argument('--port', type=int, default=4173)
    run.add_argument('--visual-tolerance', type=float, default=0.01)
    run.add_argument('--scenarios', help='JSON mapping page paths to read-only interaction scenarios')
    run.add_argument('--viewport', action='append', metavar='WIDTHxHEIGHT', help='Repeat for multiple exact browser content viewports (default: 1440x900 and 390x844)')
    for command in ('status', 'validate', 'export'):
        child = sub.add_parser(command)
        child.add_argument('--output')
        if command == 'validate':
            child.add_argument('--port', type=int, default=4173)
        if command == 'export':
            child.add_argument('--destination', help='Delivery folder (default: <website>+copied)')
    args = parser.parse_args()
    if args.command == 'capture':
        if not args.authorized:
            parser.error('--authorized is required; automated crawling is restricted to websites you own or may reproduce')
        parts = urlsplit(args.url)
        if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password:
            parser.error('--url must be an HTTP(S) URL without embedded credentials')
        if not 0 <= args.visual_tolerance <= 1:
            parser.error('--visual-tolerance must be between 0 and 1')
        output = args.output or str(default_output(args.url))
        scenarios = json.loads(Path(args.scenarios).read_text(encoding='utf-8')) if args.scenarios else None
        viewports = None
        if args.viewport:
            try:
                viewports = [[int(value) for value in viewport.lower().split('x')] for viewport in args.viewport]
                if any(len(viewport) != 2 or min(viewport) < 240 or max(viewport) > 7680 for viewport in viewports):
                    raise ValueError()
            except ValueError:
                parser.error('--viewport must be WIDTHxHEIGHT, each dimension between 240 and 7680')
        with workspace_lock(output):
            store = capture(args.url, args.crawler, output, port=args.port, allowed_ratio=args.visual_tolerance, scenarios=scenarios, viewports=viewports)
    else:
        output = args.output
        if not output:
            current = json.loads(Path('.doppelgng/current.json').read_text(encoding='utf-8'))
            output = str(Path(current['manifest']).parent)
        store = Store(output)
        if args.command == 'export':
            destination = export_project(store, args.destination)
            print(json.dumps({'project': str(destination), 'start': 'npm run dev', 'status': store.data['status']}, indent=2))
            return 0
        if args.command == 'validate':
            with workspace_lock(output), Preview(store, args.port) as preview, Waterfox(store.root / 'artifacts') as browser:
                store.data['status'] = 'validating'
                store.save()
                for url, page in store.data['pages'].items():
                    if page.get('kind') != 'page':
                        if store.verify(page['resources']):
                            page['state'] = 'failed'
                            page['validation'] = {'passed': False, 'errors': ['Download or resource integrity failed']}
                        continue
                    print(f'[regression] {url}', flush=True)
                    directory = store.artifact_dir(url)
                    baselines = json.loads((directory / 'baseline.json').read_text(encoding='utf-8'))
                    result = local_validate(browser, url, preview.origin + public_url(url, store.data['target']), directory, baselines, allowed_ratio=store.data['policy']['allowed_visual_ratio'])
                    actions = interaction_check(browser, url, preview.origin + public_url(url, store.data['target']), directory, store.data.get('scenarios', {}).get(urlsplit(url).path, []))
                    result['interactions'] = actions
                    result['passed'] &= all(action['passed'] for action in actions)
                    if not result['passed']:
                        result['errors'].append('Visual, browser, content, or interaction verification failed')
                    broken = store.verify(page['resources'])
                    result['integrity_errors'] = broken
                    result['passed'] &= not broken
                    page['validation'] = result
                    page['state'] = 'validated' if result['passed'] else 'failed'
                    store.save()
                navigation_validation(store, browser, preview)
        print(json.dumps({'status': store.data['status'], 'pages': {url: page['state'] for url, page in store.data['pages'].items()}, 'resources': len(store.data['resources']), 'manifest': str(store.path)}, indent=2))
    return 0 if args.command == 'status' or store.data['status'] == 'complete' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError) as error:
        print(f'doppelgng.me: {error}', file=sys.stderr)
        raise SystemExit(1)
