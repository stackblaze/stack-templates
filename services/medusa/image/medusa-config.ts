import { loadEnv, defineConfig } from '@medusajs/framework/utils'

loadEnv(process.env.NODE_ENV || 'production', process.cwd())

// StackBlaze build of upstream's starter config (medusajs/dtc-starter
// apps/backend/medusa-config.ts). Additions, all from upstream's production
// deployment guide and Medusa Cloud's own defaults (defineConfig):
// - Valkey (REDIS_URL) for admin sessions, the event bus, the workflow
//   engine, the cache and locking, instead of the in-memory development
//   modules.
// - Local files on the mounted volume (/server/static, served at /static),
//   with public URLs on the app's own address instead of localhost:9000.
const redisUrl = process.env.REDIS_URL
const backendUrl = (process.env.MEDUSA_BACKEND_URL || 'http://localhost:9000').replace(/\/+$/, '')

module.exports = defineConfig({
  projectConfig: {
    databaseUrl: process.env.DATABASE_URL,
    redisUrl,
    workerMode:
      (process.env.MEDUSA_WORKER_MODE as 'shared' | 'worker' | 'server') ||
      'shared',
    http: {
      storeCors: process.env.STORE_CORS!,
      adminCors: process.env.ADMIN_CORS!,
      authCors: process.env.AUTH_CORS!,
      jwtSecret: process.env.JWT_SECRET,
      cookieSecret: process.env.COOKIE_SECRET,
    },
  },
  admin: {
    // Unset at build time, so the admin calls the API on its own origin.
    backendUrl: process.env.MEDUSA_ADMIN_BACKEND_URL,
    disable: process.env.DISABLE_MEDUSA_ADMIN === 'true',
  },
  modules: [
    {
      resolve: '@medusajs/medusa/file',
      options: {
        providers: [
          {
            resolve: '@medusajs/medusa/file-local',
            id: 'local',
            options: {
              upload_dir: 'static',
              backend_url: `${backendUrl}/static`,
            },
          },
        ],
      },
    },
    ...(redisUrl
      ? [
          {
            resolve: '@medusajs/medusa/event-bus-redis',
            options: { redisUrl },
          },
          {
            resolve: '@medusajs/medusa/workflow-engine-redis',
            options: { redis: { redisUrl } },
          },
          {
            resolve: '@medusajs/medusa/cache-redis',
            options: { redisUrl },
          },
          {
            resolve: '@medusajs/medusa/locking',
            options: {
              providers: [
                {
                  resolve: '@medusajs/medusa/locking-redis',
                  id: 'locking-redis',
                  is_default: true,
                  options: { redisUrl },
                },
              ],
            },
          },
        ]
      : []),
  ],
})
