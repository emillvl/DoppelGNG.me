import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';

function run(command, args) {
  const result = spawnSync(command, args, { stdio: 'inherit', env });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed (${result.status})`);
}
const temporary = path.resolve('.tools/tmp');
mkdirSync(temporary, { recursive: true });
const env = { ...process.env, PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1', TEMP: temporary, TMP: temporary, TMPDIR: temporary };
const base = process.env.DOPPELGNG_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const local = path.resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
if (!existsSync(local)) {
  const created = spawnSync(base, ['-m', 'venv', '.venv'], { stdio: 'inherit', env });
  if (created.error) throw created.error;
  if (created.status !== 0) run(base, ['-m', 'venv', '--without-pip', '.venv']);
}
const requirements = existsSync('requirements.lock.txt') ? 'requirements.lock.txt' : 'requirements.txt';
const digest = createHash('sha256').update(readFileSync(requirements)).digest('hex');
const marker = path.resolve('.venv/doppelgng-requirements.sha256');
const check = 'import sys, importlib.metadata as m; from pathlib import Path; import requests,bs4,psutil,selenium,PIL,tinycss2,websocket; pins=[l.split("==") for l in Path(sys.argv[1]).read_text(encoding="utf-8-sig").splitlines() if "==" in l]; assert all(m.version(n)==v for n,v in pins)';
const cached = existsSync(marker) && readFileSync(marker, 'utf8') === digest && spawnSync(local, ['-c', check, requirements], { stdio: 'ignore', env }).status === 0;
if (cached) console.log('Reusing verified Python dependencies.');
else {
  const ownPip = spawnSync(local, ['-m', 'pip', '--version'], { stdio: 'ignore', env }).status === 0;
  // A bundled interpreter may create a venv without its own ensurepip.
  if (ownPip) run(local, ['-m', 'pip', 'install', '-r', requirements]);
  else run(base, ['-m', 'pip', '--python', local, 'install', '-r', requirements]);
  writeFileSync(marker, digest);
}
run(local, ['-m', 'doppelgng.bootstrap']);
