import type { MedusaRequest, MedusaResponse } from '@medusajs/framework/http'

// StackBlaze: the app URL opens the admin. Medusa serves nothing at `/`
// (Express "Cannot GET /"), and the admin lives at /app.
export const GET = (_req: MedusaRequest, res: MedusaResponse) => {
  res.redirect(302, '/app')
}
