#!/usr/bin/env node
/**
 * Upload a template demo video to Bunny Storage
 * (https://media.stackblaze.cloud/templates/<slug>/demo.mp4).
 *
 * Usage:
 *   node upload-demo-video.mjs --slug n8n --file ./renders/n8n-demo.mp4
 *
 * Auth (first match):
 *   BUNNY_STORAGE_PASSWORD + optional BUNNY_STORAGE_ZONE / BUNNY_STORAGE_HOSTNAME
 *   or a local key file at /Users/adam/passwords/bunny-templates
 */
import fs from 'node:fs';
import path from 'node:path';
import { TEMPLATE_VIDEO_CDN } from './capture-lib.mjs';

const DEFAULT_ZONE = 'stackblaze-templates';
const DEFAULT_HOST = 'ny.storage.bunnycdn.com';
const LOCAL_CREDS = '/Users/adam/passwords/bunny-templates';

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--slug') args.slug = argv[++i];
    else if (a === '--file') args.file = argv[++i];
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function loadCreds() {
  const fromEnv = {
    zone: process.env.BUNNY_STORAGE_ZONE || DEFAULT_ZONE,
    host: process.env.BUNNY_STORAGE_HOSTNAME || DEFAULT_HOST,
    password: process.env.BUNNY_STORAGE_PASSWORD || '',
  };
  if (fromEnv.password) return fromEnv;
  if (!fs.existsSync(LOCAL_CREDS)) {
    throw new Error(
      'Set BUNNY_STORAGE_PASSWORD (or create /Users/adam/passwords/bunny-templates)',
    );
  }
  const parsed = Object.fromEntries(
    fs
      .readFileSync(LOCAL_CREDS, 'utf8')
      .split('\n')
      .filter((l) => l.includes('='))
      .map((l) => l.split('=', 2)),
  );
  return {
    zone: parsed.STORAGE_ZONE || DEFAULT_ZONE,
    host: parsed.STORAGE_HOSTNAME || DEFAULT_HOST,
    password: parsed.STORAGE_PASSWORD || '',
  };
}

function usage() {
  console.log(`Upload demo.mp4 to Bunny CDN.

  node upload-demo-video.mjs --slug <slug> --file <path.mp4>
`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.slug || !args.file) {
    usage();
    process.exit(args.help ? 0 : 1);
  }
  const file = path.resolve(args.file);
  if (!fs.existsSync(file)) throw new Error(`file not found: ${file}`);
  const creds = loadCreds();
  if (!creds.password) throw new Error('storage password is empty');

  const remotePath = `templates/${args.slug}/demo.mp4`;
  const url = `https://${creds.host}/${creds.zone}/${remotePath}`;
  const body = fs.readFileSync(file);
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      AccessKey: creds.password,
      'Content-Type': 'video/mp4',
    },
    body,
  });
  if (!res.ok) {
    throw new Error(`upload failed ${res.status} ${await res.text()}`);
  }
  const publicUrl = `${TEMPLATE_VIDEO_CDN}/${args.slug}/demo.mp4`;
  console.log(`uploaded ${body.length} bytes → ${publicUrl}`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
