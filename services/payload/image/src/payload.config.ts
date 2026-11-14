import { postgresAdapter } from '@payloadcms/db-postgres'
import { nodemailerAdapter } from '@payloadcms/email-nodemailer'
import sharp from 'sharp'
import path from 'path'
import { buildConfig, type EmailAdapter, PayloadRequest } from 'payload'
import { fileURLToPath } from 'url'

import { Categories } from './collections/Categories'
import { Media } from './collections/Media'
import { Pages } from './collections/Pages'
import { Posts } from './collections/Posts'
import { Users } from './collections/Users'
import { Footer } from './Footer/config'
import { Header } from './Header/config'
import { plugins } from './plugins'
import { defaultLexical } from '@/fields/defaultLexical'
import { getServerSideURL } from './utilities/getURL'
import { createFirstAdmin } from './utilities/createFirstAdmin'

const filename = fileURLToPath(import.meta.url)
const dirname = path.dirname(filename)

// StackBlaze: send mail through the Email add-on when it is attached. It injects
// SMTP_HOST, SMTP_PORT (587, STARTTLS), SMTP_USER, SMTP_PASSWORD and SMTP_FROM,
// which may be `Name <address>`. Without SMTP_HOST, Payload logs mail to the console.
const smtpFrom = (process.env.SMTP_FROM || '').match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/)
const smtpPort = Number(process.env.SMTP_PORT || 587)
// Each sent message is logged with the relay's reply, so delivery can be checked in the app logs.
const logSentMail = async (
  adapter: ReturnType<typeof nodemailerAdapter>,
): Promise<EmailAdapter> => {
  const factory = await adapter
  return (args) => {
    const instance = factory(args)
    return {
      ...instance,
      sendEmail: async (message) => {
        const info = (await instance.sendEmail(message)) as {
          messageId?: string
          response?: string
        }
        args.payload.logger.info(
          `Email sent: ${info?.response ?? 'ok'} (message id ${info?.messageId ?? '?'})`,
        )
        return info
      },
    }
  }
}
const email = process.env.SMTP_HOST
  ? logSentMail(
      nodemailerAdapter({
        defaultFromAddress: smtpFrom ? smtpFrom[2] : process.env.SMTP_FROM || '',
        defaultFromName:
          process.env.PAYLOAD_EMAIL_FROM_NAME || (smtpFrom && smtpFrom[1]) || 'Payload',
        transportOptions: {
          host: process.env.SMTP_HOST,
          port: smtpPort,
          secure: smtpPort === 465,
          auth: process.env.SMTP_USER
            ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASSWORD }
            : undefined,
        },
      }),
    )
  : undefined

export default buildConfig({
  admin: {
    components: {
      // The `BeforeLogin` component renders a message that you see while logging into your admin panel.
      // Feel free to delete this at any time. Simply remove the line below.
      beforeLogin: ['@/components/BeforeLogin'],
      // The `BeforeDashboard` component renders the 'welcome' block that you see after logging into your admin panel.
      // Feel free to delete this at any time. Simply remove the line below.
      beforeDashboard: ['@/components/BeforeDashboard'],
    },
    importMap: {
      baseDir: path.resolve(dirname),
    },
    user: Users.slug,
    livePreview: {
      breakpoints: [
        {
          label: 'Mobile',
          name: 'mobile',
          width: 375,
          height: 667,
        },
        {
          label: 'Tablet',
          name: 'tablet',
          width: 768,
          height: 1024,
        },
        {
          label: 'Desktop',
          name: 'desktop',
          width: 1440,
          height: 900,
        },
      ],
    },
  },
  // This config helps us configure global or default features that the other editors can inherit
  editor: defaultLexical,
  email,
  db: postgresAdapter({
    pool: {
      connectionString: process.env.DATABASE_URL || '',
    },
  }),
  collections: [Pages, Posts, Media, Categories, Users],
  cors: [getServerSideURL()].filter(Boolean),
  globals: [Header, Footer],
  plugins,
  // StackBlaze: create the first admin from PAYLOAD_ADMIN_EMAIL / PAYLOAD_ADMIN_PASSWORD
  // while the users collection is empty, so no visitor can claim the site.
  onInit: createFirstAdmin,
  secret: process.env.PAYLOAD_SECRET,
  sharp,
  typescript: {
    outputFile: path.resolve(dirname, 'payload-types.ts'),
  },
  // StackBlaze: liveness for the platform health check, served once Payload has
  // initialised (connected to Postgres). GET /api/health -> {"status":"ok"}.
  endpoints: [
    {
      path: '/health',
      method: 'get',
      handler: () => Response.json({ status: 'ok' }),
    },
  ],
  jobs: {
    // StackBlaze: this is a long-running server, so run the job queue in-process
    // every minute. Scheduled publishing (Schedule Publish on pages and posts)
    // queues jobs; upstream leaves running them to an external (Vercel) cron.
    autoRun: [{ cron: '* * * * *', allQueues: true }],
    access: {
      run: ({ req }: { req: PayloadRequest }): boolean => {
        // Allow logged in users to execute this endpoint (default)
        if (req.user) return true

        const secret = process.env.CRON_SECRET
        if (!secret) return false

        // If there is no logged in user, then check
        // for the Vercel Cron secret to be present as an
        // Authorization header:
        const authHeader = req.headers.get('authorization')
        return authHeader === `Bearer ${secret}`
      },
    },
    tasks: [],
  },
})
