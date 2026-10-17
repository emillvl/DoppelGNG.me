import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

function run(command, args) {
  const result = spawnSync(command, args, { stdio: 'inherit', env: { ...process.env, PYTHONUTF8: '1' } });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed (${result.status})`);
}
const base = process.env.DOPPELGNG_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const local = path.resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
if (!existsSync(local)) run(base, ['-m', 'venv', '.venv']);
// --python also supports a venv created without its own pip.
run(base, ['-m', 'pip', '--python', local, 'install', '-r', existsSync('requirements.lock.txt') ? 'requirements.lock.txt' : 'requirements.txt']);
run(local, ['-m', 'doppelgng.bootstrap']);
