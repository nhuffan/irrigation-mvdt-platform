import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const source = readFileSync(new URL('../src/app/api/rag-lite/route.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;

function proxy() {
  const exports = {};
  const queries = [];
  vm.runInNewContext(compiled, {
    exports, process: { env: { API_BASE_URL: 'http://api.test/api/v1' } },
    URL, Response, AbortSignal, TextDecoder,
    require: () => ({ MANAGED_RESERVOIR_ID: 'managed-reservoir' }),
    fetch: async (_url, options) => {
      queries.push(JSON.parse(options.body));
      return Response.json({ status: 'RETRIEVAL_ONLY' });
    },
  });
  const post = headers => exports.POST(new Request('http://localhost:3300/api/rag-lite', {
    method: 'POST', headers, body: JSON.stringify({ question: 'Historical evidence' }),
  }));
  return { post, queries };
}

test('RAG browser origin uses incoming Host when Next canonicalizes the URL', async () => {
  const { post, queries } = proxy();
  const response = await post({ host: '127.0.0.1:3300', origin: 'http://127.0.0.1:3300' });
  assert.equal(response.status, 200);
  assert.deepEqual(queries, [{ question: 'Historical evidence', reservoir_id: 'managed-reservoir' }]);
});

test('RAG rejects origins that match only an internal or forwarded hostname', async () => {
  const { post, queries } = proxy();
  const response = await post({ host: '127.0.0.1:3300', origin: 'http://localhost:3300', 'x-forwarded-host': 'localhost:3300' });
  assert.equal(response.status, 403);
  assert.deepEqual(queries, []);
  assert.equal((await post({ host: '127.0.0.1:3300, localhost:3300', origin: 'http://127.0.0.1:3300' })).status, 403);
});

test('RAG supports clients without Origin and falls back to the URL without Host', async () => {
  const { post, queries } = proxy();
  assert.equal((await post({ host: '127.0.0.1:3300' })).status, 200);
  assert.equal((await post({ origin: 'http://localhost:3300' })).status, 200);
  assert.equal((await post({ origin: 'http://other.test:3300' })).status, 403);
  assert.equal(queries.length, 2);
});
