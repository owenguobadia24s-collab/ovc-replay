#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { getHistoricalRates } = require('dukascopy-node');

const [yearMonth, workspaceRoot] = process.argv.slice(2);
if (!/^202[1-5]-(0[1-9]|1[0-2])$/.test(yearMonth || '')) {
  throw new Error(`invalid WP4 year-month: ${yearMonth}`);
}
if (!workspaceRoot || !path.isAbsolute(workspaceRoot)) {
  throw new Error('workspace root must be an absolute path outside the Git worktree');
}

const [year, month] = yearMonth.split('-').map(Number);
const start = new Date(Date.UTC(year, month - 1, 1));
const end = month === 12
  ? new Date(Date.UTC(year + 1, 0, 1))
  : new Date(Date.UTC(year, month, 1));
const role = year <= 2023 ? 'discovery' : year === 2024 ? 'development' : 'validation';
const objects = [
  ['m1', 'bid'],
  ['m1', 'ask'],
  ['h1', 'bid'],
  ['h1', 'ask'],
];

function upper(value) {
  return value.toUpperCase();
}

async function downloadObject(timeframe, priceType) {
  const targetDir = path.join(workspaceRoot, 'source', role, timeframe, priceType);
  const cacheDir = path.join(workspaceRoot, 'transport_cache', timeframe, priceType, yearMonth);
  await fs.mkdir(targetDir, { recursive: true });
  await fs.mkdir(cacheDir, { recursive: true });
  const target = path.join(
    targetDir,
    `GBPUSD_${upper(timeframe)}_${upper(priceType)}_${yearMonth}_UTC.csv`,
  );

  console.log(`WP4 download start ${yearMonth} ${timeframe.toUpperCase()} ${priceType.toUpperCase()}`);
  const csv = await getHistoricalRates({
    instrument: 'gbpusd',
    dates: { from: start, to: end },
    timeframe,
    priceType,
    format: 'csv',
    utcOffset: 0,
    volumes: true,
    volumeUnits: 'units',
    ignoreFlats: true,
    batchSize: 8,
    pauseBetweenBatchesMs: 500,
    useCache: true,
    cacheFolderPath: cacheDir,
    retryCount: 4,
    retryOnEmpty: false,
    failAfterRetryCount: false,
    pauseBetweenRetriesMs: 1500,
  });

  if (typeof csv !== 'string' || !csv.startsWith('timestamp,open,high,low,close,volume')) {
    const observedType = csv === null ? 'null' : typeof csv;
    throw new Error(
      `unexpected ${timeframe}/${priceType} response for ${yearMonth}; type=${observedType}`,
    );
  }
  const payload = csv.endsWith('\n') ? csv : `${csv}\n`;
  await fs.writeFile(target, payload, { encoding: 'utf8', flag: 'wx' });
  console.log(`WP4 download complete ${yearMonth} ${timeframe.toUpperCase()} ${priceType.toUpperCase()} bytes=${Buffer.byteLength(payload, 'utf8')}`);
  return target;
}

const downloaded = [];
for (const [timeframe, priceType] of objects) {
  downloaded.push(await downloadObject(timeframe, priceType));
}

const receipt = {
  schema: 'ovc-opt-a-wp4-downloader-receipt/v1',
  provider: 'DUKASCOPY',
  adapter: 'dukascopy-node',
  adapter_version: '1.46.4',
  instrument_id: 'GBPUSD',
  year_month: yearMonth,
  interval_start: start.toISOString(),
  interval_end: end.toISOString(),
  role: role.toUpperCase(),
  downloaded_files: downloaded.map((item) => path.relative(workspaceRoot, item).split(path.sep).join('/')),
  source_object_count: downloaded.length,
  raw_transport_cache_retained: true,
  market_authority: 'NONE',
  release_parent: 'DENIED_UNTIL_FREEZE',
  selector_input: 'DENIED',
};
const receiptPath = path.join(workspaceRoot, 'records', 'downloader', `${yearMonth}.json`);
await fs.mkdir(path.dirname(receiptPath), { recursive: true });
await fs.writeFile(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
console.log(JSON.stringify(receipt));
