import http from 'node:http';
import { createReadStream, existsSync, readFileSync, statSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function sortedQuery(search, omit = []) {
  const query = new URLSearchParams(search);
  for (const name of omit) query.delete(name);
  query.sort();
  return query.toString();
}

export function findResource(manifest, requestUrl, headers = {}) {
  const original = new URL(manifest.target);
  const resources = Object.values(manifest.resources);
  if (requestUrl.pathname.startsWith('/__doppelgng__/asset/')) {
    return resources.find(r => r.key === requestUrl.pathname.split('/').at(-1));
  }
  const candidates = resources.filter(r => {
    const url = new URL(r.url);
    return url.origin === original.origin && url.pathname === requestUrl.pathname && r.method === 'GET';
  });
  const exact = candidates.find(r => sortedQuery(new URL(r.url).search) === sortedQuery(requestUrl.search));
  if (exact) return exact;
  // Static export flight files use a request nonce; the body is a file at this path.
  const volatile = manifest.policy?.volatile_static_query ?? [];
  const staticVariant = candidates.find(r => r.kind !== 'page' && !r.content_type.includes('json') && sortedQuery(new URL(r.url).search, volatile) === sortedQuery(requestUrl.search, volatile));
  if (staticVariant) return staticVariant;
  // Redirect aliases can contain a document with no separate canonical record.
  return resources.find(r => {
    if (r.kind !== 'page' || r.method !== 'GET' || !r.final_url) return false;
    const final = new URL(r.final_url);
    return final.origin === original.origin && final.pathname === requestUrl.pathname && sortedQuery(final.search) === sortedQuery(requestUrl.search);
  });
}

export function createPreviewServer(manifestPath) {
  const absoluteManifest = path.resolve(manifestPath);
  const root = path.dirname(absoluteManifest);
  const failures = [];
  const server = http.createServer((request, response) => {
    const send = (status, text) => {
      response.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' });
      response.end(request.method === 'HEAD' ? undefined : text);
    };
    try {
      const url = new URL(request.url, 'http://localhost');
      if (url.pathname === '/__doppelgng__/health') return send(200, 'ready');
      if (!existsSync(absoluteManifest)) return send(503, 'No reconstruction yet. Run npm run crawl -- --help to start an authorized capture.');
      const manifest = JSON.parse(readFileSync(absoluteManifest, 'utf8'));
      if (url.pathname === '/__doppelgng__/report') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
        return response.end(JSON.stringify({ ...manifest, server_failures: failures }, null, 2));
      }
      if (url.pathname === '/__doppelgng__/failures') {
        response.writeHead(200, { 'Content-Type': 'application/json' });
        return response.end(JSON.stringify(failures));
      }
      if (!['GET', 'HEAD'].includes(request.method)) {
        failures.push({ method: request.method, url: request.url, status: 501 });
        return send(501, 'This server-side operation was not captured. Configure and verify a local service adapter.');
      }
      const record = findResource(manifest, url, request.headers);
      if (!record) {
        const alternate = new URL(url);
        alternate.pathname = url.pathname.endsWith('/') ? url.pathname.slice(0, -1) : url.pathname + '/';
        const page = findResource(manifest, alternate);
        if (page?.kind === 'page') {
          response.writeHead(308, { Location: alternate.pathname + url.search });
          return response.end();
        }
        failures.push({ method: request.method, url: request.url, status: 404 });
        return send(404, `Uncaptured resource: ${request.url}`);
      }
      if (record.kind === 'page' && record.final_url) {
        const final = new URL(record.final_url);
        if (final.origin === new URL(manifest.target).origin && final.pathname + final.search !== url.pathname + url.search) {
          response.writeHead(302, { Location: final.pathname + final.search });
          return response.end();
        }
      }
      const file = path.resolve(root, record.local);
      const allowed = path.resolve(root, 'site') + path.sep;
      if (!file.startsWith(allowed) || !existsSync(file) || !realpathSync(file).startsWith(realpathSync(path.resolve(root, 'site')) + path.sep)) return send(404, 'Resource file is unavailable');
      const size = statSync(file).size;
      const headers = { 'Content-Type': record.content_type, 'Cache-Control': 'no-store', 'Accept-Ranges': 'bytes', 'X-Content-Type-Options': 'nosniff' };
      const documentTypes = new Set(['text/html', 'application/xhtml+xml', 'image/svg+xml', 'text/xml', 'application/xml']);
      const contentType = record.content_type.split(';', 1)[0].trim().toLowerCase();
      const originalOrigin = new URL(manifest.target).origin;
      if (documentTypes.has(contentType) && [record.url, record.final_url].filter(Boolean).some(url => new URL(url).origin !== originalOrigin)) {
        // Keep external documents isolated across iframe, object, embed, and redirects.
        headers['Content-Security-Policy'] = 'sandbox allow-scripts allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-downloads allow-pointer-lock allow-presentation';
      }
      if (record.headers?.['content-disposition']) headers['Content-Disposition'] = record.headers['content-disposition'];
      let start = 0, end = size - 1, status = record.status || 200;
      if (request.headers.range) {
        const match = /^bytes=(\d*)-(\d*)$/.exec(request.headers.range);
        if (!match || (!match[1] && !match[2])) {
          response.writeHead(416, { 'Content-Range': `bytes */${size}` });
          return response.end();
        }
        start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
        end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
        if (start > end || start >= size) {
          response.writeHead(416, { 'Content-Range': `bytes */${size}` });
          return response.end();
        }
        status = 206;
        headers['Content-Range'] = `bytes ${start}-${end}/${size}`;
      }
      headers['Content-Length'] = Math.max(0, end - start + 1);
      response.writeHead(status, headers);
      if (request.method === 'HEAD' || size === 0) return response.end();
      const stream = createReadStream(file, { start, end });
      stream.on('error', () => response.destroy());
      stream.pipe(response);
    } catch (error) {
      if (!response.headersSent) send(500, `Reconstruction error: ${error.message}`);
      else response.destroy();
    }
  });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  const argument = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
  let manifest = argument('--manifest', process.env.DOPPELGNG_MANIFEST);
  if (!manifest && existsSync('.doppelgng/current.json')) manifest = JSON.parse(readFileSync('.doppelgng/current.json', 'utf8')).manifest;
  manifest ||= '.doppelgng/manifest.json';
  const port = Number(argument('--port', process.env.PORT || '4173'));
  const server = createPreviewServer(manifest);
  server.on('error', error => { console.error(error.message); process.exitCode = 1; });
  server.listen(port, '127.0.0.1', () => console.log(`doppelgng.me  Local: http://127.0.0.1:${server.address().port}\nCapture: ${path.resolve(manifest)}`));
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close(() => process.exit(0)));
}
