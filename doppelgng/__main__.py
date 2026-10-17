import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from .pipeline import capture, Preview, navigation_validation
from .browser import Waterfox
from .storage import Store, workspace_lock, incomplete_on_failure, now
from .validation import local_validate, interaction_check
from .reconstruct import public_url
from .export import default_output, export_project
from .dependencies import default_crawler
from .network import DestinationDenied, origin
from .authentication import login_scope


def non_negative_int(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('must be a non-negative integer') from error
    if number < 0:
        raise argparse.ArgumentTypeError('must be a non-negative integer')
    return number


def build_parser():
    parser = argparse.ArgumentParser(description='Capture an authorized website and verify its local replay with headless Waterfox.')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('capture', help='Discover in-scope pages, archive resources, and validate local replay')
    run.add_argument('--url', required=True)
    run.add_argument('--authorized', action='store_true', help='Confirm you own this website or are authorized to reproduce it')
    run.add_argument('--authorize-resource-origin', action='append', metavar='URL', help='Authorize an additional resource origin, including private networks. Repeat for each origin you own or may reproduce; redirects to other private origins remain blocked. Saved for resume')
    run.add_argument('--crawler', default=str(default_crawler()), help='Optional crawler override; defaults to the pinned project-local crawler installed by npm run setup')
    run.add_argument('--output', help='Capture folder (default: the website domain)')
    run.add_argument('--port', type=int, default=4173)
    run.add_argument('--visual-tolerance', type=float, default=0.01)
    run.add_argument('--scenarios', help='JSON mapping page paths to read-only interaction scenarios')
    run.add_argument('--viewport', action='append', metavar='WIDTHxHEIGHT', help='Repeat for multiple exact browser content viewports (default: 1440x900 and 390x844)')
    robots = run.add_mutually_exclusive_group()
    robots.add_argument('--ignore-robots', dest='respect_robots', action='store_false', help='Skip robots.txt rules for this capture')
    robots.add_argument('--respect-robots', dest='respect_robots', action='store_true', help='Apply robots.txt rules (default)')
    run.set_defaults(respect_robots=True)
    run.add_argument('--checkpoint-every', type=non_negative_int, default=1, metavar='N', help='Save the crawler checkpoint every N pages (default: 1; 0 disables periodic saves). Final saves and reconstruction recovery records remain enabled')
    run.add_argument('-q', '--quiet', action='store_true', help='Suppress DoppelGNG.me progress; keep the final JSON result and errors')
    login_options(run)
    for command in ('status', 'validate', 'export'):
        child = sub.add_parser(command)
        child.add_argument('--output')
        if command == 'validate':
            child.add_argument('--port', type=int, default=4173)
            login_options(child)
        if command == 'export':
            child.add_argument('--destination', help='Delivery folder (default: the website domain)')
    return parser


def login_options(parser):
    parser.add_argument('--login', action='store_true', help='Prompt for hidden credentials and use an in-memory same-origin HTML-form session')
    parser.add_argument('--login-url', metavar='URL', help='Login page on the target origin (default: follow the target to its login form)')
    parser.add_argument('--login-check', metavar='SELECTOR', help='Required with --login: CSS selector visible on every signed-in HTML page')
    parser.add_argument('--login-form', metavar='SELECTOR', help='Select one password form when automatic selection is ambiguous')
    parser.add_argument('--login-user-field', metavar='NAME', help='Username input name when automatic selection is ambiguous')
    parser.add_argument('--login-password-field', metavar='NAME', help='Password input name when automatic selection is ambiguous')


def main(argv=None):
    parser = build_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(value.startswith('--login=') or (value == '--login' and index + 1 < len(arguments) and not arguments[index + 1].startswith('-')) for index, value in enumerate(arguments)):
        parser.error('--login takes no credential argument. Enter credentials only at the hidden prompts.')
    args = parser.parse_args(arguments)
    if hasattr(args, 'login'):
        settings = (args.login_url, args.login_check, args.login_form, args.login_user_field, args.login_password_field)
        if any(settings) and not args.login:
            parser.error('Login options require --login. Supply credentials only at its hidden prompts.')
        if args.login and not args.login_check:
            parser.error('--login requires --login-check with a signed-in page selector')
    if args.command == 'capture':
        if not args.authorized:
            parser.error('--authorized is required; automated crawling is restricted to websites you own or may reproduce')
        parts = urlsplit(args.url)
        if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password:
            parser.error('--url must be an HTTP(S) URL without embedded credentials')
        if not 0 <= args.visual_tolerance <= 1:
            parser.error('--visual-tolerance must be between 0 and 1')
        if args.authorize_resource_origin:
            try:
                for value in args.authorize_resource_origin:
                    origin(value)
            except DestinationDenied as error:
                parser.error(str(error))
        output = args.output or str(default_output(args.url))
        if args.login and (Path(output) / 'manifest.json').exists():
            parser.error('Use a fresh --output directory with --login; saved authenticated captures cannot be resumed')
        scenarios = json.loads(Path(args.scenarios).read_text(encoding='utf-8')) if args.scenarios else None
        viewports = None
        if args.viewport:
            try:
                viewports = [[int(value) for value in viewport.lower().split('x')] for viewport in args.viewport]
                if any(len(viewport) != 2 or min(viewport) < 240 or max(viewport) > 7680 for viewport in viewports):
                    raise ValueError()
            except ValueError:
                parser.error('--viewport must be WIDTHxHEIGHT, each dimension between 240 and 7680')
        with workspace_lock(output), (login_scope(args.url, args) if args.login else nullcontext()) as authentication:
            options = {'authentication': authentication} if authentication else {}
            store = capture(args.url, args.crawler, output, port=args.port, allowed_ratio=args.visual_tolerance, scenarios=scenarios, viewports=viewports, respect_robots=args.respect_robots, checkpoint_every=args.checkpoint_every, quiet=args.quiet, authorized_resource_origins=args.authorize_resource_origin, **options)
    else:
        output = args.output
        if not output:
            current = json.loads(Path('.doppelgng/current.json').read_text(encoding='utf-8'))
            output = str(Path(current['manifest']).parent)
        store = Store(output)
        if args.command == 'export':
            with workspace_lock(output):
                store = Store(output)
                destination = export_project(store, args.destination)
            print(json.dumps({'project': str(destination), 'start': 'npm run dev', 'status': store.data['status']}, indent=2))
            return 0
        if args.command == 'validate':
            with workspace_lock(output):
                store = Store(output)
                if store.data.get('authentication', {}).get('required') and not args.login:
                    parser.error('This capture requires fresh authentication: validate with --login and --login-check')
                with (login_scope(store.data['target'], args) if args.login else nullcontext()) as authentication:
                    return validate_capture(store, args, authentication)
        print(json.dumps({'status': store.data['status'], 'pages': {url: page['state'] for url, page in store.data['pages'].items()}, 'resources': len(store.data['resources']), 'manifest': str(store.path)}, indent=2))
    return 0 if args.command == 'status' or store.data['status'] == 'complete' else 1


def validate_capture(store, args, authentication=None):
    store.authentication = authentication
    options = {'authentication': authentication} if authentication else {}
    with incomplete_on_failure(store), Preview(store, args.port) as preview, Waterfox(store.root / 'artifacts', **options) as browser:
        store.data['status'] = 'validating'
        store.data.pop('error', None)
        store.save()
        for url, page in store.data['pages'].items():
            if page.get('kind') != 'page':
                if page.get('kind') != 'download' or store.verify(page['resources']):
                    page['state'] = 'failed'
                    page['validation'] = {'passed': False, 'errors': ['Download or resource integrity failed']}
                else:
                    page['state'] = 'download_validated'
                    page['validation'] = {'passed': True, 'checked_at': now(), 'applicable': 'archived original and replay resource hash integrity'}
                store.save()
                continue
            page['state'] = 'validating'
            store.save()
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
    return 0 if store.data['status'] == 'complete' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError) as error:
        print(f'doppelgng.me: {error}', file=sys.stderr)
        raise SystemExit(1)
