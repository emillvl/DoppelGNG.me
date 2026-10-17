import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { createPreviewServer } from '../server.mjs';

test('serves routes, exact query variants, flight nonce, HEAD and download ranges without network fallback', async () => {
  mkdirSync('.tools/test-temp', { recursive: true });
  const root = mkdtempSync(path.resolve('.tools/test-temp/server-'));
  mkdirSync(path.join(root, 'site'));
  writeFileSync(path.join(root, 'site/page'), '<title>nested</title>');
  writeFileSync(path.join(root, 'site/file'), 'abcdef');
  writeFileSync(path.join(root, 'site/flight'), 'flight');
  const resources = {
    a: { url: 'https://example.test/nested/', local: 'site/page', method: 'GET', kind: 'page', content_type: 'text/html' },
    b: { url: 'https://example.test/file.zip?v=1', local: 'site/file', method: 'GET', kind: 'resource', content_type: 'application/zip' },
    c: { url: 'https://example.test/nested/tree.txt?_rsc=one', local: 'site/flight', method: 'GET', kind: 'resource', content_type: 'text/plain' },
  };
  writeFileSync(path.join(root, 'manifest.json'), JSON.stringify({ target: 'https://example.test/', resources, policy: { volatile_static_query: ['_rsc'] } }));
  const server = createPreviewServer(path.join(root, 'manifest.json'));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    assert.equal((await fetch(base + '/nested/')).status, 200);
    assert.equal((await fetch(base + '/nested')).url, base + '/nested/');
    assert.equal(await (await fetch(base + '/nested/tree.txt?_rsc=two')).text(), 'flight');
    assert.equal((await fetch(base + '/file.zip?v=2')).status, 404);
    const range = await fetch(base + '/file.zip?v=1', { headers: { Range: 'bytes=1-3' } });
    assert.equal(range.status, 206);
    assert.equal(await range.text(), 'bcd');
    const head = await fetch(base + '/nested/', { method: 'HEAD' });
    assert.equal(head.headers.get('content-length'), '21');
    assert.equal(await head.text(), '');
    assert.equal((await fetch(base + '/api', { method: 'POST' })).status, 501);
    assert.equal((await fetch(base + '/missing')).status, 404);
    assert.equal((await fetch(base + '/file.zip?v=1', { headers: { Range: 'bytes=9-10' } })).status, 416);
  } finally {
    await new Promise(resolve => server.close(resolve));
    rmSync(root, { recursive: true });
  }
});

test('refuses local paths escaping the reconstructed site', async () => {
  mkdirSync('.tools/test-temp', { recursive: true });
  const root = mkdtempSync(path.resolve('.tools/test-temp/escape-'));
  mkdirSync(path.join(root, 'site'));
  writeFileSync(path.join(root, 'secret'), 'private');
  writeFileSync(path.join(root, 'manifest.json'), JSON.stringify({ target: 'https://example.test/', resources: { a: { url: 'https://example.test/', local: 'secret', method: 'GET', kind: 'page' } } }));
  const server = createPreviewServer(path.join(root, 'manifest.json'));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { assert.equal((await fetch(`http://127.0.0.1:${server.address().port}`)).status, 404); }
  finally { await new Promise(resolve => server.close(resolve)); rmSync(root, { recursive: true }); }
});
