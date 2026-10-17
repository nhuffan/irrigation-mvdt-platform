import test from 'node:test';
import assert from 'node:assert/strict';
import {
  satelliteConfig, STREET_LAYER, HISTORICAL_LAYERS,
  cameraZoomLimit, effectiveTileZoom, cappedCameraZoom,
  tileCoordinate, tileUrl, redactProviderUrl,
  loadSatelliteLayer, SatelliteProviderError,
} from '../src/lib/satellite-provider.ts';

// Synthetic values only: these tests never inspect environment keys or use the network.
const fakeKey = 'unit_test_owner_key_123';
const center = [106.340773, 11.323022];
const config = () => satelliteConfig({ provider: 'maptiler', maptilerKey: fakeKey });
const metadata = overrides => ({
  tiles: [`https://api.maptiler.com/tiles/unit-satellite-current/{z}/{x}/{y}.jpg?key=${fakeKey}`],
  minzoom: 0, maxzoom: 22, attribution: 'MapTiler test credits',
  bounds: [-180, -85, 180, 85], ...overrides,
});
const style = (overrides = {}, raster = {}) => ({
  version: 8,
  sources: {
    imagery: { type: 'raster', url: `https://api.maptiler.com/tiles/unit-satellite-current/tiles.json?key=${fakeKey}`, ...raster },
  },
  layers: [{ id: 'imagery', type: 'raster', source: 'imagery' }], ...overrides,
});
const json = value => new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
const image = () => new Response(new Uint8Array([1, 2, 3]), { headers: { 'content-type': 'image/jpeg' } });
const decoder256 = async () => ({ width: 256, height: 256 });
function queueFetch(...responses) {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url: String(url), options });
    const next = responses.shift();
    if (next instanceof Error) throw next;
    assert.ok(next, 'unexpected fetch; tests have no network fallback');
    return typeof next === 'function' ? next() : next;
  };
  return { fetcher, calls };
}
function queueMaptiler(...responses) { return queueFetch(json(style()), ...responses); }
function safeError(code) {
  return error => {
    assert.ok(error instanceof SatelliteProviderError);
    assert.equal(error.code, code);
    assert.equal(error.message, code);
    assert.ok(!`${error.message} ${error.stack}`.includes(fakeKey));
    assert.ok(!/https?:\/\//.test(error.message));
    return true;
  };
}
const isAbort = error => {
  assert.equal(error.name, 'AbortError');
  assert.ok(!error.message.includes(fakeKey));
  return true;
};

test('missing or invalid config cannot issue a premium request', async () => {
  for (const input of [
    {}, { provider: null }, { maptilerKey: null }, { maptilerKey: '' },
    { provider: 'unknown', maptilerKey: fakeKey }, { provider: {} },
    { maptilerKey: 12345678 }, { maptilerKey: 'your_api_key_here' },
    { maptilerKey: 'invalid key' }, { maptilerKey: 'https://key.invalid' },
    { provider: 'esri', maptilerKey: fakeKey },
  ]) {
    const result = satelliteConfig(input);
    assert.equal(result.status, 'CONFIGURATION_REQUIRED');
    let requested = false;
    await assert.rejects(loadSatelliteLayer(result, center, new AbortController().signal,
      async () => { requested = true; throw new Error('must never fetch'); }, decoder256), safeError('AUTH_REQUIRED'));
    assert.equal(requested, false);
    assert.ok(!JSON.stringify(result).includes(fakeKey));
  }
  assert.deepEqual(satelliteConfig({ provider: 'auto', esriKey: fakeKey }),
    { status: 'CONFIGURED', provider: 'esri', key: fakeKey });
  assert.equal(config().provider, 'maptiler');
});

test('street fallback and historical layers remain honestly labeled and independently capped', () => {
  assert.equal(STREET_LAYER.kind, 'street');
  assert.equal(STREET_LAYER.provider, 'osm');
  assert.match(STREET_LAYER.date, /not satellite/i);
  assert.match(STREET_LAYER.attribution, /OpenStreetMap contributors/);
  assert.equal(cameraZoomLimit(STREET_LAYER), 18);
  assert.equal(HISTORICAL_LAYERS.length, 2);
  for (const layer of HISTORICAL_LAYERS) {
    assert.equal(layer.kind, 'historical');
    assert.equal(layer.provider, 'nasa');
    assert.equal(layer.tileSize, 256);
    assert.equal(cameraZoomLimit(layer), layer.maxzoom - 1);
    assert.equal(cappedCameraZoom(18, layer), layer.maxzoom - 1);
    assert.equal(effectiveTileZoom(cameraZoomLimit(layer), layer), layer.maxzoom);
    assert.ok(layer.tiles.every(url => url.startsWith('https://gibs.earthdata.nasa.gov/')));
  }
});

test('native caps account for 256px raster offset and never promise detail from overscaling', () => {
  const raster = { minzoom: 0, maxzoom: 18, tileSize: 256 };
  assert.equal(cameraZoomLimit(raster), 17);
  assert.deepEqual([12, 14, 16, 18].map(zoom => effectiveTileZoom(zoom, raster)), [13, 15, 17, 18]);
  assert.equal(cappedCameraZoom(18, raster), 17);
  assert.equal(cappedCameraZoom(-1, raster), 0);
  const standard512 = { minzoom: 0, maxzoom: 16, tileSize: 512 };
  assert.equal(cameraZoomLimit(standard512), 16);
  assert.equal(effectiveTileZoom(14, standard512), 14);
  assert.equal(effectiveTileZoom(30, standard512), 16);
  assert.equal(cameraZoomLimit({ maxzoom: 24, tileSize: 512 }), 18);
});

test('tile coordinate substitution is bounded at poles and antimeridian', () => {
  assert.deepEqual(tileCoordinate(0, 0, 1), { x: 1, y: 1 });
  assert.deepEqual(tileCoordinate(180, 90, 2), { x: 3, y: 0 });
  assert.deepEqual(tileCoordinate(-180, -90, 2), { x: 0, y: 3 });
  assert.equal(tileUrl('https://tiles.invalid/{z}/{x}/{y}', 1, [0, 0]), 'https://tiles.invalid/1/1/1');
});

test('provider metadata is followed by a real image-response check and decoded dimensions govern tileSize', async () => {
  const queued = queueMaptiler(json(metadata()), image());
  const controller = new AbortController();
  let decoded = false;
  const result = await loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, async response => {
    assert.equal(response.headers.get('content-type'), 'image/jpeg');
    assert.deepEqual([...new Uint8Array(await response.arrayBuffer())], [1, 2, 3]);
    decoded = true;
    return { width: 512, height: 512 };
  });
  assert.equal(decoded, true);
  assert.equal(result.tileSize, 512);
  assert.equal(result.maxzoom, 22);
  assert.equal(result.detailMaxZoom, 16);
  assert.equal(cameraZoomLimit(result), 16);
  assert.equal(cappedCameraZoom(18, result), 16);
  assert.equal(result.kind, 'satellite');
  assert.match(result.date, /varies/);
  assert.equal(queued.calls.length, 3);
  assert.match(queued.calls[0].url, /^https:\/\/api\.maptiler\.com\/maps\/satellite\/style\.json\?key=/);
  assert.match(queued.calls[1].url, /^https:\/\/api\.maptiler\.com\/tiles\/unit-satellite-current\/tiles\.json\?key=/);
  assert.match(queued.calls[2].url, /\/unit-satellite-current\/12\/\d+\/\d+\.jpg\?key=/);
  assert.ok(queued.calls.every(call => !call.url.includes('satellite-v4')));
  for (const call of queued.calls) {
    assert.equal(call.options.signal, controller.signal);
    assert.equal(call.options.credentials, 'omit');
  }
});

test('Esri requires authorized metadata and retains supplied attribution', async () => {
  const esri = satelliteConfig({ provider: 'esri', esriKey: fakeKey });
  const queued = queueFetch(json({
    copyrightText: 'Esri test attribution',
    tileInfo: { spatialReference: { wkid: 3857 }, lods: [{ level: 0 }, { level: 18 }] },
  }), image());
  const result = await loadSatelliteLayer(esri, center, new AbortController().signal, queued.fetcher, decoder256);
  assert.equal(result.provider, 'esri');
  assert.equal(result.attribution, 'Esri test attribution');
  assert.equal(result.maxzoom, 18);
  assert.match(queued.calls[1].url, /^https:\/\/ibasemaps-api\.arcgis\.com\/arcgis\/rest\/services\/World_Imagery\/MapServer\/tile\/12\/\d+\/\d+\?token=/);
  const rejected = queueFetch(json({ error: { code: 498, message: `key ${fakeKey}` } }));
  await assert.rejects(loadSatelliteLayer(esri, center, new AbortController().signal, rejected.fetcher, decoder256), safeError('AUTH_REQUIRED'));
  assert.equal(rejected.calls.length, 1);
});

test('HTTP authorization, quota, coverage and server failures produce safe codes at style, metadata or image stage', async () => {
  for (const [status, code] of [[401, 'AUTH_REQUIRED'], [403, 'AUTH_REQUIRED'], [429, 'QUOTA_EXCEEDED'], [204, 'COVERAGE_UNAVAILABLE'], [404, 'COVERAGE_UNAVAILABLE'], [503, 'PROVIDER_UNAVAILABLE']]) {
    for (const stage of [0, 1, 2]) {
      const failed = new Response(status === 204 ? null : `provider URL ?key=${fakeKey}`, { status });
      const previous = stage === 0 ? [] : stage === 1 ? [json(style())] : [json(style()), json(metadata())];
      const queued = queueFetch(...previous, failed);
      await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError(code));
      assert.equal(queued.calls.length, stage + 1);
    }
  }
});

test('untrusted tile URLs, wrong protocols and missing coordinates are rejected before imagery fetch', async () => {
  for (const template of [
    'http://api.maptiler.com/{z}/{x}/{y}.jpg',
    'https://untrusted.invalid/{z}/{x}/{y}.jpg',
    'https://api.maptiler.com.untrusted.invalid/{z}/{x}/{y}.jpg',
    'https://ibasemaps-api.arcgis.com/{z}/{x}/{y}.jpg',
    'https://user:password@api.maptiler.com/{z}/{x}/{y}.jpg',
    'https://api.maptiler.com/{z}/{x}.jpg',
    'https://api.maptiler.com:8443/{z}/{x}/{y}.jpg',
    'data:image/png;base64,AAAA',
  ]) {
    const queued = queueMaptiler(json(metadata({ tiles: [template] })));
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('METADATA_INVALID'));
    assert.equal(queued.calls.length, 2);
  }
});

test('unusable provider metadata cannot be mistaken for available imagery', async () => {
  for (const value of [null, [], {}, metadata({ tiles: [] }), metadata({ attribution: '' }),
    metadata({ maxzoom: 25 }), metadata({ minzoom: 12, maxzoom: 9 }), metadata({ maxzoom: '18' })]) {
    const queued = queueMaptiler(json(value));
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('METADATA_INVALID'));
    assert.equal(queued.calls.length, 2);
  }
  const outside = queueMaptiler(json(metadata({ bounds: [-10, -10, 10, 10] })));
  await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, outside.fetcher, decoder256), safeError('COVERAGE_UNAVAILABLE'));
  assert.equal(outside.calls.length, 2);
});

test('invalid image media and decoded geometry are rejected, including metadata dimension disagreement', async () => {
  for (const dimensions of [{ width: 1, height: 1 }, { width: 512, height: 256 }, { width: 1024, height: 1024 }]) {
    const queued = queueMaptiler(json(metadata()), image());
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher,
      async () => dimensions), safeError('METADATA_INVALID'));
  }
  const disagreement = queueMaptiler(json(metadata({ tileSize: 512 })), image());
  await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, disagreement.fetcher, decoder256), safeError('METADATA_INVALID'));
  const html = queueMaptiler(json(metadata()), new Response(`<html>key=${fakeKey}</html>`, { headers: { 'content-type': 'text/html' } }));
  await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, html.fetcher,
    async () => assert.fail('HTML must not be decoded as imagery')), safeError('METADATA_INVALID'));
});

test('network, parser and decoder messages cannot leak keyed URLs', async () => {
  const secretUrl = `https://api.maptiler.com/tiles.json?key=${fakeKey}`;
  const cases = [
    queueFetch(new Error(`style fetch failed ${secretUrl}`)),
    queueMaptiler(new Error(`metadata fetch failed ${secretUrl}`)),
    queueFetch(new Response(`malformed style JSON ${secretUrl}`, { headers: { 'content-type': 'application/json' } })),
    queueMaptiler(new Response(`malformed metadata JSON ${secretUrl}`, { headers: { 'content-type': 'application/json' } })),
    queueMaptiler(json(metadata({ tiles: [`not a URL ?key=${fakeKey}`] }))),
  ];
  for (const queued of cases) await assert.rejects(
    loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('PROVIDER_UNAVAILABLE'));
  const queued = queueMaptiler(json(metadata()), image());
  await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher,
    async () => { throw new Error(`decode failed ${secretUrl}`); }), safeError('PROVIDER_UNAVAILABLE'));
});

test('aborted requests expose AbortError instead of provider URLs', async () => {
  const controller = new AbortController();
  const queued = queueFetch(() => { controller.abort(); throw new Error(`aborted ?key=${fakeKey}`); });
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, decoder256), isAbort);
});

test('a pre-aborted signal cannot fetch or resolve a provider', async () => {
  const controller = new AbortController();
  controller.abort();
  const queued = queueMaptiler(json(metadata()), image());
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, decoder256), isAbort);
  assert.equal(queued.calls.length, 0);
});

test('abort after metadata prevents the next imagery request even if a transport resolves late', async () => {
  const controller = new AbortController();
  const queued = queueMaptiler(() => { controller.abort(); return json(metadata()); }, image());
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, decoder256), isAbort);
  assert.equal(queued.calls.length, 2);
});

test('abort during image decoding cannot publish a stale satellite layer', async () => {
  const controller = new AbortController();
  const queued = queueMaptiler(json(metadata()), image());
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, async () => {
    controller.abort();
    return { width: 256, height: 256 };
  }), isAbort);
});

test('diagnostic URL redaction covers provider credential query names without hiding tile coordinates', () => {
  for (const name of ['key', 'token', 'access_token', 'api_key', 'KEY', 'Token']) {
    const redacted = redactProviderUrl(`https://tiles.invalid/18/1/2.jpg?f=json&${name}=${fakeKey}#map`);
    assert.ok(!redacted.includes(fakeKey));
    assert.match(redacted, /\/18\/1\/2\.jpg\?f=json&/);
    assert.match(redacted, /\[redacted\]#map$/);
  }
  assert.equal(redactProviderUrl('https://tiles.invalid/18/1/2.jpg'), 'https://tiles.invalid/18/1/2.jpg');
});

test('style discovery uses only raster sources referenced by raster layers and retains source credits/dimensions', async () => {
  const rasterStyle = style({}, { tileSize: 512, attribution: 'Style raster credits' });
  rasterStyle.sources.unused = { type: 'raster', url: 'https://untrusted.invalid/not-requested.json' };
  rasterStyle.layers.push({ id: 'imagery-second-use', type: 'raster', source: 'imagery' });
  const queued = queueFetch(json(rasterStyle), json(metadata({ scheme: 'xyz', crs: 'EPSG:3857', format: 'JPEG' })), image());
  const result = await loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher,
    async () => ({ width: 512, height: 512 }));
  assert.equal(queued.calls.length, 3);
  assert.ok(queued.calls.every(call => !call.url.includes('untrusted.invalid')));
  assert.equal(result.tileSize, 512);
  assert.equal(result.maxzoom, 22);
  assert.equal(cameraZoomLimit(result), 16);
  assert.equal(effectiveTileZoom(cameraZoomLimit(result), result), 16);
  assert.match(result.attribution, /MapTiler test credits/);
  assert.match(result.attribution, /Style raster credits/);
  const disagreement = queueFetch(json(rasterStyle), json(metadata()), image());
  await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, disagreement.fetcher, decoder256), safeError('METADATA_INVALID'));
});

test('absent, ambiguous or non-raster Satellite style sources fail before any TileJSON request', async () => {
  const multiple = style();
  multiple.sources.second = { type: 'raster', url: `https://api.maptiler.com/tiles/second/tiles.json?key=${fakeKey}` };
  multiple.layers.push({ id: 'second', type: 'raster', source: 'second' });
  for (const value of [null, [], {}, style({ sources: {} }), style({ layers: [] }),
    style({ layers: [{ id: 'missing-source', type: 'raster' }] }), style({}, { type: 'vector' }),
    style({}, { url: undefined }), multiple]) {
    const queued = queueFetch(json(value));
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('METADATA_INVALID'));
    assert.equal(queued.calls.length, 1);
  }
});

test('style-discovered TileJSON URL is restricted to official HTTPS tile paths without credentials or ports', async () => {
  for (const url of [
    'http://api.maptiler.com/tiles/unit/tiles.json',
    'https://untrusted.invalid/tiles/unit/tiles.json',
    'https://api.maptiler.com.untrusted.invalid/tiles/unit/tiles.json',
    'https://user:password@api.maptiler.com/tiles/unit/tiles.json',
    'https://api.maptiler.com:8443/tiles/unit/tiles.json',
    'https://api.maptiler.com/maps/unit/style.json',
    'https://api.maptiler.com/tiles/unit/other.json',
    'https://api.maptiler.com/tiles/unit/nested/tiles.json',
  ]) {
    const queued = queueFetch(json(style({}, { url })));
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('METADATA_INVALID'));
    assert.equal(queued.calls.length, 1);
  }
});

test('incompatible TileJSON scheme, projection or vector format cannot silently misplace imagery', async () => {
  for (const override of [{ scheme: 'tms' }, { scheme: 'XYZ' }, { crs: 'EPSG:4326' },
    { crs: { name: 'EPSG:3857' } }, { format: 'pbf' }, { format: 'mvt' }, { format: 'html' }]) {
    const queued = queueMaptiler(json(metadata(override)));
    await assert.rejects(loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256), safeError('METADATA_INVALID'));
    assert.equal(queued.calls.length, 2);
  }
  for (const override of [{ crs: 'EPSG:900913', scheme: 'xyz', format: 'png' }, { format: 'webp' }]) {
    const queued = queueMaptiler(json(metadata(override)), image());
    const result = await loadSatelliteLayer(config(), center, new AbortController().signal, queued.fetcher, decoder256);
    assert.equal(result.kind, 'satellite');
    assert.equal(queued.calls.length, 3);
  }
});

test('abort after parsed style stops discovery before TileJSON fetch', async () => {
  const controller = new AbortController();
  const response = json(style());
  response.json = async () => { controller.abort(); return style(); };
  const queued = queueFetch(response, json(metadata()), image());
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher, decoder256), isAbort);
  assert.equal(queued.calls.length, 1);
});

test('abort at imagery fetch completion prevents decoding and stale publication', async () => {
  const controller = new AbortController();
  const queued = queueMaptiler(json(metadata()), () => { controller.abort(); return image(); });
  await assert.rejects(loadSatelliteLayer(config(), center, controller.signal, queued.fetcher,
    async () => assert.fail('aborted image must not be decoded')), isAbort);
  assert.equal(queued.calls.length, 3);
});
