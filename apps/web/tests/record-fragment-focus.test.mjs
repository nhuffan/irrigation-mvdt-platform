import test from 'node:test';
import assert from 'node:assert/strict';
import { observeRecordFragment } from '../src/lib/record-fragment-focus.ts';

const RECORD = '55555555-5555-4555-8555-555555555555';
const OTHER = '22222222-2222-4222-8222-222222222222';

function withPage(hash, run) {
  const original = { window: globalThis.window, document: globalThis.document };
  const events = new EventTarget();
  const calls = [];
  const records = new Map();
  const article = {
    scrollIntoView: options => calls.push(['scroll', options]),
    focus: options => calls.push(['focus', options]),
  };
  globalThis.window = {
    location: { hash },
    addEventListener: events.addEventListener.bind(events),
    removeEventListener: events.removeEventListener.bind(events),
  };
  globalThis.document = { getElementById: id => records.get(id) ?? null };
  try { run({ calls, records, article, navigate: hash => {
    window.location.hash = hash;
    events.dispatchEvent(new Event('hashchange'));
  } }); } finally {
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
}

test('a record arriving after fragment navigation is scrolled into view and focused on mount', () => {
  withPage(`#record-${RECORD}`, ({ calls, records, article }) => {
    assert.equal(document.getElementById(`record-${RECORD}`), null);
    records.set(`record-${RECORD}`, article);
    const stop = observeRecordFragment([RECORD]);
    assert.deepEqual(calls, [['scroll', { block: 'center' }], ['focus', { preventScroll: true }]]);
    stop();
  });
});

test('unrelated fragments, another asset record, and absent targets never move focus', () => {
  withPage('#technical', ({ calls, records, article, navigate }) => {
    records.set(`record-${OTHER}`, article);
    const stop = observeRecordFragment([RECORD]);
    for (const hash of ['', `#record-${OTHER}`, `#record-${RECORD}/child`, `#record-${RECORD}`]) navigate(hash);
    assert.deepEqual(calls, []);
    stop();
  });
});

test('same-page record navigation works and unmount removes its observer', () => {
  withPage('', ({ calls, records, article, navigate }) => {
    records.set(`record-${RECORD}`, article);
    const stop = observeRecordFragment([RECORD]);
    assert.deepEqual(calls, []);
    navigate(`#record-${RECORD}`);
    assert.equal(calls.length, 2);
    stop();
    navigate(`#record-${RECORD}`);
    assert.equal(calls.length, 2);
  });
});
