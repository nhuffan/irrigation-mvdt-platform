import test from 'node:test';
import assert from 'node:assert/strict';
import { rasterClarityPaint, nativeDetailZoom, closerDetailZoom, streetFailureAction } from '../src/lib/observation-detail.ts';
import { loadStreetVectorLayer } from '../src/lib/street-vector.ts';
import { satelliteConfig, STREET_LAYER, HISTORICAL_LAYERS, cameraZoomLimit, cappedCameraZoom, SatelliteProviderError } from '../src/lib/satellite-provider.ts';

// Synthetic owner configuration only. No environment access, credentials or network.
const fakeKey = 'unit_test_street_owner_123';
const config = () => satelliteConfig({ provider: 'maptiler', maptilerKey: fakeKey });
const signal = () => new AbortController().signal;
const json = value => new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
const style = () => ({
  version: 8, name: 'Synthetic provider vector style',
  glyphs: `https://api.maptiler.com/fonts/{fontstack}/{range}.pbf?key=${fakeKey}`,
  sprite: `https://api.maptiler.com/maps/unit-streets/sprite?key=${fakeKey}`,
  sources: { basemap: { type: 'vector', url: `https://api.maptiler.com/tiles/unit-streets/tiles.json?key=${fakeKey}`, attribution: 'Synthetic contributor credit' } },
  layers: [
    { id: 'background', type: 'background', paint: { 'background-color': '#fff' } },
    { id: 'water', type: 'fill', source: 'basemap', 'source-layer': 'water', paint: { 'fill-color': '#aaf' } },
    { id: 'labels', type: 'symbol', source: 'basemap', 'source-layer': 'place', layout: { 'text-field': ['get', 'name'] } },
  ],
});
const fakeFetch = value => async () => json(value);
const safeError = code => error => {
  assert.ok(error instanceof SatelliteProviderError);
  assert.equal(error.code, code);
  assert.equal(error.message, code);
  assert.ok(!`${error.message} ${error.stack}`.includes(fakeKey));
  assert.ok(!/https?:\/\//.test(error.message));
  return true;
};
const aborted = error => {
  assert.equal(error.name, 'AbortError');
  assert.ok(!`${error.message} ${error.stack}`.includes(fakeKey));
  return true;
};

test('all raster layers replace newly loaded detail without blending source levels', () => {
  for (const kind of ['satellite', 'historical', 'street']) {
    for (const rendering of ['smooth', 'original']) {
      const paint = rasterClarityPaint({ kind }, rendering);
      assert.equal(paint['raster-fade-duration'], 0);
      assert.equal(paint['raster-resampling'], kind === 'historical' && rendering === 'original' ? 'nearest' : 'linear');
    }
  }
});

test('native detail snaps fractional views and never stretches NASA above its source cap', () => {
  const satellite = { ...STREET_LAYER, kind: 'satellite', tileSize: 512, maxzoom: 22, detailMaxZoom: 16 };
  for (const layer of [STREET_LAYER, satellite, ...HISTORICAL_LAYERS]) {
    assert.equal(nativeDetailZoom(7.49, layer), 7);
    assert.equal(nativeDetailZoom(7.51, layer), 8);
    assert.equal(nativeDetailZoom(30, layer), cameraZoomLimit(layer));
    assert.equal(nativeDetailZoom(-1, layer), 0);
    assert.equal(closerDetailZoom(layer), layer.kind === 'street' ? cameraZoomLimit(layer) : Math.min(16, cameraZoomLimit(layer)));
  }
  assert.deepEqual(HISTORICAL_LAYERS.map(layer => closerDetailZoom(layer)), [11, 8]);
});

test('a failed vector street map falls back to OSM once and raster failures stop', () => {
  assert.equal(streetFailureAction(true, false), 'USE_OSM');
  assert.equal(streetFailureAction(true, true), 'SHOW_ERROR');
  assert.equal(streetFailureAction(false, false), 'SHOW_ERROR');
  assert.equal(streetFailureAction(false, true), 'SHOW_ERROR');
});

test('street style requests use only the configured MapTiler owner key with abort and credential omission', async () => {
  const sourceStyle = style();
  const controller = new AbortController();
  const calls = [];
  const layer = await loadStreetVectorLayer(config(), controller.signal, async (url, options) => {
    calls.push({ url, options });
    return json(sourceStyle);
  });
  assert.equal(calls.length, 1);
  const url = new URL(calls[0].url);
  assert.equal(url.origin, 'https://api.maptiler.com');
  assert.equal(url.pathname, '/maps/streets/style.json');
  assert.equal(url.searchParams.get('key'), fakeKey);
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.signal, controller.signal);
  assert.equal(layer.id, 'street');
  assert.equal(layer.kind, 'street');
  assert.equal(layer.provider, 'maptiler');
  assert.equal(layer.renderMode, 'vector');
  assert.match(layer.date, /not satellite/i);
  assert.match(layer.attribution, /MapTiler/);
  assert.match(layer.attribution, /OpenStreetMap contributors/);
  assert.deepEqual(layer.style, sourceStyle, 'provider glyphs, sprites, layer order and contributor credits must survive');
  assert.deepEqual(layer.tiles, [], 'vector rendering must not use a raster replacement');
});

test('vector camera detail is independent of source tile extent while raster caps still apply', async () => {
  const vector = await loadStreetVectorLayer(config(), signal(), fakeFetch(style()));
  assert.equal(cameraZoomLimit(vector), 18);
  assert.equal(cameraZoomLimit({ ...vector, maxzoom: 14 }), 18);
  assert.equal(cameraZoomLimit({ ...vector, detailMaxZoom: 17 }), 17);
  assert.equal(cappedCameraZoom(24, vector), 18);
  assert.equal(closerDetailZoom(vector), 18);
  assert.equal(nativeDetailZoom(17.8, vector), 18);
  assert.equal(cameraZoomLimit({ maxzoom: 14, tileSize: 512 }), 14);
  assert.equal(cameraZoomLimit({ maxzoom: 14, tileSize: 256 }), 13);
});

test('missing config and Esri ownership never issue MapTiler street requests', async () => {
  for (const input of [satelliteConfig({}), satelliteConfig({ provider: 'esri', esriKey: fakeKey })]) {
    let requested = false;
    await assert.rejects(loadStreetVectorLayer(input, signal(), async () => {
      requested = true;
      throw new Error('must not use another provider');
    }), safeError('AUTH_REQUIRED'));
    assert.equal(requested, false);
  }
});

test('street HTTP auth, quota and service failures are classified without keyed URLs', async () => {
  for (const [status, code] of [[401, 'AUTH_REQUIRED'], [403, 'AUTH_REQUIRED'], [429, 'QUOTA_EXCEEDED'], [404, 'PROVIDER_UNAVAILABLE'], [503, 'PROVIDER_UNAVAILABLE']]) {
    await assert.rejects(loadStreetVectorLayer(config(), signal(), async () => new Response(null, { status })), safeError(code));
  }
});

test('network and parser exceptions cannot leak provider request URLs', async () => {
  const privateMessage = `Failed https://api.maptiler.com/maps/unit/style.json?key=${fakeKey}`;
  await assert.rejects(loadStreetVectorLayer(config(), signal(), async () => { throw new Error(privateMessage); }), safeError('PROVIDER_UNAVAILABLE'));
  await assert.rejects(loadStreetVectorLayer(config(), signal(), async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError(privateMessage); } })), safeError('PROVIDER_UNAVAILABLE'));
});

test('malformed StyleJSON and unresolved source references cannot initialize a street map', async () => {
  const invalid = [null, [], {}, { ...style(), version: 7 }, { ...style(), layers: [] }, { ...style(), layers: {} }, { ...style(), sources: [] }, { ...style(), sources: {} }, { ...style(), layers: [{ id: 'unresolved', type: 'fill', source: 'missing' }] }, { ...style(), layers: [{ id: 'only-background', type: 'background' }] }];
  for (const value of invalid) {
    await assert.rejects(loadStreetVectorLayer(config(), signal(), fakeFetch(value)), safeError('METADATA_INVALID'));
  }
});

test('every resource-bearing source must be a provider vector source, even when unused', async () => {
  const invalidSources = [
    { type: 'raster', url: 'https://api.maptiler.com/tiles/unit/tiles.json' },
    { type: 'vector', tiles: ['https://api.maptiler.com/tiles/unit/{z}/{x}/{y}.pbf'] },
    { type: 'vector', url: 'https://api.maptiler.com/tiles/unit/tiles.json', tiles: ['https://other.invalid/{z}/{x}/{y}.pbf'] },
    null,
    { type: 'vector', url: 'https://other.invalid/tiles.json' },
    { type: 'vector', url: 'http://api.maptiler.com/tiles.json' },
    { type: 'vector', url: 'https://api.maptiler.com:444/tiles.json' },
    { type: 'vector', url: 'https://user:pass@api.maptiler.com/tiles.json' },
    { type: 'vector', url: 'https://api.maptiler.com/tiles.json#fragment' },
    { type: 'vector', url: 'https://api.maptiler.com.other.invalid/tiles.json' },
    { type: 'vector', url: 'not a URL' },
    { type: 'vector' },
    { type: 'vector', attribution: 123 },
  ];
  for (const extra of invalidSources) {
    const value = style();
    value.sources.extra = extra;
    await assert.rejects(loadStreetVectorLayer(config(), signal(), fakeFetch(value)), safeError('METADATA_INVALID'));
  }
});

test('glyph and sprite resources reject external, active, authenticated or port-changing URLs', async () => {
  const invalidAssets = [undefined, null, 'http://api.maptiler.com/resource', 'https://other.invalid/resource', 'javascript:alert(1)', 'https://user:pass@api.maptiler.com/resource', 'https://api.maptiler.com:444/resource', 'https://api.maptiler.com/resource#fragment', 'not a URL'];
  for (const field of ['glyphs', 'sprite']) {
    for (const asset of invalidAssets) {
      const value = style();
      value[field] = asset;
      await assert.rejects(loadStreetVectorLayer(config(), signal(), fakeFetch(value)), safeError('METADATA_INVALID'));
    }
  }
  for (const sprite of [[], [{}], [{ id: 'extra', url: 'https://other.invalid/sprite' }]]) {
    await assert.rejects(loadStreetVectorLayer(config(), signal(), fakeFetch({ ...style(), sprite })), safeError('METADATA_INVALID'));
  }
});

test('multiple provider sprite sets remain intact for vector text and icon rendering', async () => {
  const sourceStyle = { ...style(), sprite: [{ id: 'default', url: 'https://api.maptiler.com/maps/unit/sprite' }, { id: 'extra', url: 'https://api.maptiler.com/maps/unit-extra/sprite' }] };
  const layer = await loadStreetVectorLayer(config(), signal(), fakeFetch(sourceStyle));
  assert.deepEqual(layer.style.sprite, sourceStyle.sprite.map(sprite => ({ ...sprite, url: `${sprite.url}?key=${fakeKey}` })));
});

test('already-aborted requests never fetch and expose only AbortError', async () => {
  const controller = new AbortController();
  controller.abort(`private provider URL ?key=${fakeKey}`);
  let requested = false;
  await assert.rejects(loadStreetVectorLayer(config(), controller.signal, async () => { requested = true; return json(style()); }), aborted);
  assert.equal(requested, false);
});

test('abort after fetch wins over HTTP failures and prevents style parsing', async () => {
  const controller = new AbortController();
  let parsed = false;
  await assert.rejects(loadStreetVectorLayer(config(), controller.signal, async () => {
    controller.abort(`key=${fakeKey}`);
    return { ok: false, status: 403, json: async () => { parsed = true; return style(); } };
  }), aborted);
  assert.equal(parsed, false);
});

test('abort during JSON parsing cannot return a late ready layer', async () => {
  const controller = new AbortController();
  await assert.rejects(loadStreetVectorLayer(config(), controller.signal, async () => ({
    ok: true, status: 200,
    json: async () => { controller.abort(`key=${fakeKey}`); return style(); },
  })), aborted);
});


test('real provider attribution-only source survives without adding a new tile request', async () => {
  const sourceStyle = style();
  sourceStyle.sources.maptiler_attribution = { type: 'vector', attribution: 'Required provider contributor credit' };
  const layer = await loadStreetVectorLayer(config(), signal(), fakeFetch(sourceStyle));
  assert.deepEqual(layer.style.sources.maptiler_attribution, sourceStyle.sources.maptiler_attribution);
  assert.deepEqual(layer.style.sources.basemap, sourceStyle.sources.basemap);
  const usedStub = { ...sourceStyle, layers: [...sourceStyle.layers, { id: 'invalid-use', type: 'line', source: 'maptiler_attribution', 'source-layer': 'water' }] };
  await assert.rejects(loadStreetVectorLayer(config(), signal(), fakeFetch(usedStub)), safeError('METADATA_INVALID'));
});

test('unkeyed official style resources receive only the owner key without encoding template braces', async () => {
  const sourceStyle = style();
  sourceStyle.sources.basemap.url = 'https://api.maptiler.com/tiles/unit/tiles.json?language=en';
  sourceStyle.glyphs = 'https://api.maptiler.com/fonts/{fontstack}/{range}.pbf';
  sourceStyle.sprite = 'https://api.maptiler.com/maps/unit/sprite';
  const layer = await loadStreetVectorLayer(config(), signal(), fakeFetch(sourceStyle));
  assert.equal(layer.style.sources.basemap.url, `https://api.maptiler.com/tiles/unit/tiles.json?language=en&key=${fakeKey}`);
  assert.equal(layer.style.glyphs, `https://api.maptiler.com/fonts/{fontstack}/{range}.pbf?key=${fakeKey}`);
  assert.equal(layer.style.sprite, `https://api.maptiler.com/maps/unit/sprite?key=${fakeKey}`);
  assert.ok(!layer.style.glyphs.includes('%7B'), 'font URL placeholders must remain substitutable by MapLibre');
});
