import { readFile, writeFile } from 'node:fs/promises';
import { yearSnapshot } from '../src/data/current-year.mjs';

const file = new URL('../dist/data/latest.json', import.meta.url);
const snapshot = JSON.parse(await readFile(file, 'utf8'));
await writeFile(file, JSON.stringify(yearSnapshot(snapshot)) + '\n');