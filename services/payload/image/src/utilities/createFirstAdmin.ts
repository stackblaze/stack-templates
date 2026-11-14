import type { Payload } from 'payload'

// StackBlaze: claim the site on first start so no visitor can register the first
// admin at /admin (POST /api/users/first-register only works while the users
// collection is empty). The catalog template sets PAYLOAD_ADMIN_EMAIL and a
// generated PAYLOAD_ADMIN_PASSWORD; without both, Payload behaves as upstream.
//
// Runs from the config's onInit, i.e. in the Next.js server after
// docker-entrypoint.sh has applied the migrations (`payload migrate` itself runs
// with onInit disabled), and before Payload serves any request: every request
// awaits the same init. Idempotent: once any user exists it does nothing, so
// restarts, redeploys and a changed or deleted admin are left alone. Two pods
// racing on an empty database both try the insert; the unique email index lets
// one win and the other sees the user on its re-check. The password is never logged.
export const createFirstAdmin = async (payload: Payload): Promise<void> => {
  const email = process.env.PAYLOAD_ADMIN_EMAIL?.trim()
  const password = process.env.PAYLOAD_ADMIN_PASSWORD
  if (!email || !password) return

  const hasUser = async () =>
    (await payload.count({ collection: 'users', overrideAccess: true })).totalDocs > 0

  if (await hasUser()) return

  try {
    await payload.create({
      collection: 'users',
      data: { email, password, name: 'Admin' },
      overrideAccess: true,
    })
    payload.logger.info(`Created the first admin user ${email} (password in PAYLOAD_ADMIN_PASSWORD)`)
  } catch (err) {
    if (await hasUser()) {
      payload.logger.info('First admin user already created by another instance')
      return
    }
    // Fail closed: an unclaimed site is the thing this guards against, so let
    // init fail (the health check restarts the pod) rather than serve it open.
    // Only the error's name and code are logged: a database error message can
    // echo the insert's parameters (the password hash and salt).
    const e = err as { name?: string; code?: string; cause?: { code?: string } }
    const code = e?.code ?? e?.cause?.code
    payload.logger.error(
      `Could not create the first admin user ${email}: ${e?.name ?? 'Error'}${code ? ` (${code})` : ''}`,
    )
    throw new Error('Could not create the first admin user from PAYLOAD_ADMIN_EMAIL')
  }
}
