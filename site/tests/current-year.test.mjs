import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import test from 'node:test';
import { yearSnapshot } from '../src/data/current-year.mjs';

const dist = (path) => new URL(`../dist/${path}`, import.meta.url);
const year = new Date().getUTCFullYear();

test('published pages and feed contain only current-year entries', async () => {
  const home = await readFile(dist('index.html'), 'utf8');
  assert.ok(home.includes(`Regional timeline · ${year}`), 'missing current-year timeline');
  const [, entries] = home.match(/id="incident-data"[^>]*>(.*?)<\/script>/s);
  assert.ok(JSON.parse(entries).every((entry) => entry.date.startsWith(`${year}-`)));
  const rss = await readFile(dist('rss.xml'), 'utf8');
  const dates = Array.from(rss.matchAll(/<pubDate>(.*?)<\/pubDate>/g), ([, date]) => new Date(date));
  assert.ok(dates.every((date) => date.getUTCFullYear() === year));
  const routes = (await readdir(dist('blog/'), { withFileTypes: true })).filter((item) => item.isDirectory());
  assert.equal(routes.length, dates.length);
  assert.doesNotMatch(home, /\/blog\/(dutch-caribbean-cyber-wave|mfa-is-not-a-wall)\//);
  assert.ok(routes.every(({ name }) => !['dutch-caribbean-cyber-wave', 'mfa-is-not-a-wall'].includes(name)));
});

test('year boundaries exclude missing dates, previous years and next years', () => {
  const snapshot = yearSnapshot({
    reports: [null, '2025-12-31T23:59:59Z', '2026-01-01', '2026-12-31', '2027-01-01']
      .map((published) => ({ published })),
    indicators: [
      { valid_from: '2025-12-31', created_at: '2026-03-01' },
      { created_at: '2026-02-01' },
      { value: 'undated' },
    ],
    series: [{ date: '2025-12-31' }, { date: '2026-01-01' }],
  }, 2026);
  assert.deepEqual(snapshot.reports.map((row) => row.published), ['2026-01-01', '2026-12-31']);
  assert.deepEqual(snapshot.indicators, [{ created_at: '2026-02-01' }]);
  assert.deepEqual(snapshot.series, [{ date: '2026-01-01' }]);
});

test('the built data file excludes unscoped totals and out-of-year rows', async () => {
  const snapshot = JSON.parse(await readFile(dist('data/latest.json'), 'utf8'));
  for (const key of ['kpis', 'counts_by_type', 'indicator_mix']) assert.ok(!(key in snapshot), key);
  for (const [key, date] of [['reports', 'published'], ['series', 'date'], ['indicators', 'valid_from']]) {
    assert.ok(snapshot[key].every((row) => (row[date] ?? row.created_at)?.startsWith(`${year}-`)), key);
  }
});
