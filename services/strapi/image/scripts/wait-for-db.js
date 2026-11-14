// Wait until the database accepts TCP connections before Strapi starts.
// On a fresh deploy the app and its Postgres add-on start together, and
// Strapi exits on the first ECONNREFUSED, which sends the pod into
// CrashLoopBackOff for minutes. Skipped for sqlite or without DATABASE_HOST.
const net = require('net');

const host = process.env.DATABASE_HOST;
const port = parseInt(process.env.DATABASE_PORT || '5432', 10);
const timeoutS = parseInt(process.env.DATABASE_WAIT_SECONDS || '300', 10);

if (!host || (process.env.DATABASE_CLIENT || 'sqlite') === 'sqlite') process.exit(0);

const started = Date.now();
let logged = false;
(function attempt() {
  const sock = net.connect({ host, port, timeout: 3000 });
  sock.once('connect', () => {
    sock.end();
    if (logged) console.log(`[wait-for-db] ${host}:${port} is up after ${Math.round((Date.now() - started) / 1000)}s`);
    process.exit(0);
  });
  const retry = (err) => {
    sock.destroy();
    if (!logged) { console.log(`[wait-for-db] waiting for ${host}:${port} (${err.code || err.message})`); logged = true; }
    if (Date.now() - started > timeoutS * 1000) {
      console.error(`[wait-for-db] ${host}:${port} not reachable after ${timeoutS}s`);
      process.exit(1);
    }
    setTimeout(attempt, 2000);
  };
  sock.once('error', retry);
  sock.once('timeout', () => retry(new Error('timeout')));
})();
