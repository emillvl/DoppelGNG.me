import { existsSync, mkdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

export function pythonPath() {
  const local = path.resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  return existsSync(local) ? local : (process.env.DOPPELGNG_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'));
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename)) {
  const temporary = path.resolve('.tools/tmp');
  const verifyOnly = process.argv[2] === '-m' && process.argv[3] === 'doppelgng.bootstrap' && process.argv.slice(4).includes('--offline');
  if (!verifyOnly) mkdirSync(temporary, { recursive: true });
  const result = spawnSync(pythonPath(), process.argv.slice(2), {
    stdio: 'inherit', env: { ...process.env, PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1', ...(verifyOnly ? {} : { TMP: temporary, TEMP: temporary, TMPDIR: temporary }) },
  });
  if (result.error) console.error(`Python could not start: ${result.error.message}. Run npm run setup.`);
  process.exit(result.status ?? 1);
}
