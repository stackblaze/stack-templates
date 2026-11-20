import { MedusaContainer } from '@medusajs/framework'
import { ContainerRegistrationKeys, Modules } from '@medusajs/framework/utils'

/**
 * StackBlaze: create the first admin user on a new database, so a fresh
 * deploy is never open for someone else to claim. Medusa runs each migration
 * script once (`medusa db:migrate`, tracked in `script_migrations`), before
 * the server starts. Same steps as upstream's `medusa user -e … -p …` CLI
 * (packages/medusa/src/commands/user.ts): create the user, register an
 * email/password identity, link the two.
 *
 * Credentials come from MEDUSA_ADMIN_EMAIL and MEDUSA_ADMIN_PASSWORD (a
 * generated secret). If any user exists already, nothing is changed.
 */
export default async function stackblazeAdmin({
  container,
}: {
  container: MedusaContainer
}) {
  const logger = container.resolve(ContainerRegistrationKeys.LOGGER)
  const email = process.env.MEDUSA_ADMIN_EMAIL?.trim()
  const password = process.env.MEDUSA_ADMIN_PASSWORD

  if (!email || !password) {
    logger.warn(
      '[stackblaze] MEDUSA_ADMIN_EMAIL / MEDUSA_ADMIN_PASSWORD not set: no admin user created. Create one with `npx medusa user`.'
    )
    return
  }

  const userService = container.resolve(Modules.USER)
  const [, count] = await userService.listAndCountUsers({}, { take: 1 })
  if (count > 0) {
    logger.info('[stackblaze] admin user exists already; skipping')
    return
  }

  const workflowService = container.resolve(Modules.WORKFLOW_ENGINE)
  const authService = container.resolve(Modules.AUTH)

  const { result: users } = await workflowService.run('create-users-workflow', {
    input: { users: [{ email }] },
  })
  const user = users[0]

  const { authIdentity, error } = await authService.register('emailpass', {
    body: { email, password },
  })
  if (error || !authIdentity) {
    throw new Error(`[stackblaze] could not register the admin identity: ${error}`)
  }

  await authService.updateAuthIdentities({
    id: authIdentity.id,
    app_metadata: { user_id: user.id },
  })

  logger.info(`[stackblaze] admin user ${email} created`)
}
