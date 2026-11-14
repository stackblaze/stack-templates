import type { Core } from '@strapi/strapi';

const config = ({ env }: Core.Config.Shared.ConfigParams): Core.Config.Server => ({
  host: env('HOST', '0.0.0.0'),
  port: env.int('PORT', 1337),
  // Public URL of the app (StackBlaze sets it from the app's domain). Strapi
  // uses it for absolute links: admin password-reset mails, media URLs.
  url: env('PUBLIC_URL', ''),
  // TLS ends at the StackBlaze edge. Trust X-Forwarded-* so the secure admin
  // session cookie is accepted on the plain-HTTP hop to the pod.
  proxy: { koa: env.bool('IS_PROXIED', true) },
  app: {
    keys: env.array('APP_KEYS')!,
  },
  webhooks: {
    populateRelations: env.bool('WEBHOOKS_POPULATE_RELATIONS', false),
  },
});

export default config;
