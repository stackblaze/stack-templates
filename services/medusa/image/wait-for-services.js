// Waits until Postgres accepts a real login (not just an open port) and, when
// REDIS_URL is set, until Valkey answers PING. Add-ons can come up after the
// app pod, and the operator creates the database user some seconds after the
// port opens. Gives up after about 5 minutes so the pod restarts visibly.
const { createRequire } = require('module')
const appRequire = createRequire('/server/package.json')
const { Client } = appRequire('pg')
const Redis = appRequire('ioredis')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const TRIES = 100

async function waitPostgres() {
  for (let i = 1; i <= TRIES; i++) {
    const client = new Client({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false },
      connectionTimeoutMillis: 5000,
    })
    try {
      await client.connect()
      await client.query('select 1')
      await client.end()
      if (i > 1) console.log('[stackblaze] database ready')
      return
    } catch (err) {
      try { await client.end() } catch (_) {}
      console.log(`[stackblaze] waiting for the database (${i}): ${err.code || err.message}`)
      await sleep(3000)
    }
  }
  console.log('[stackblaze] database not reachable; stopping')
  process.exit(1)
}

async function waitRedis() {
  if (!process.env.REDIS_URL) return
  for (let i = 1; i <= TRIES; i++) {
    const redis = new Redis(process.env.REDIS_URL, {
      lazyConnect: true,
      maxRetriesPerRequest: 0,
      retryStrategy: () => null,
      connectTimeout: 5000,
    })
    redis.on('error', () => {})
    try {
      await redis.connect()
      await redis.ping()
      redis.disconnect()
      if (i > 1) console.log('[stackblaze] Valkey ready')
      return
    } catch (err) {
      redis.disconnect()
      console.log(`[stackblaze] waiting for Valkey (${i}): ${err.code || err.message}`)
      await sleep(3000)
    }
  }
  console.log('[stackblaze] Valkey not reachable; stopping')
  process.exit(1)
}

waitPostgres()
  .then(waitRedis)
  .then(() => process.exit(0))
