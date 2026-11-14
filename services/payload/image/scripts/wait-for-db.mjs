// StackBlaze: wait for Postgres before migrating. On a fresh deploy the app can
// start before its database add-on accepts connections.
import pg from 'pg'

const url = process.env.DATABASE_URL
if (!url) {
  console.error('DATABASE_URL is not set')
  process.exit(1)
}
const deadline = Date.now() + Number(process.env.DB_WAIT_SECONDS || 300) * 1000
const started = Date.now()
for (let attempt = 1; ; attempt++) {
  const client = new pg.Client({ connectionString: url, connectionTimeoutMillis: 5000 })
  try {
    await client.connect()
    await client.query('select 1')
    await client.end()
    console.log(`Postgres is up after ${Math.round((Date.now() - started) / 1000)}s`)
    break
  } catch (err) {
    await client.end().catch(() => {})
    if (Date.now() > deadline) {
      console.error(`Postgres not reachable: ${err.code || err.message}`)
      process.exit(1)
    }
    if (attempt === 1 || attempt % 10 === 0)
      console.log(`Waiting for Postgres (${err.code || err.message})`)
    await new Promise((r) => setTimeout(r, 2000))
  }
}
