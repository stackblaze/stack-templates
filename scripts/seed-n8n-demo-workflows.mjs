#!/usr/bin/env node
/** @deprecated Use services/n8n/seed-demo.mjs */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const seed = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../services/n8n/seed-demo.mjs');
const child = spawn(process.execPath, [seed, ...process.argv.slice(2)], { stdio: 'inherit' });
child.on('exit', (code) => process.exit(code ?? 1));
