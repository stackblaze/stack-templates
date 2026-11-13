import PageTemplate, { generateMetadata } from './[slug]/page'

export default PageTemplate

export { generateMetadata }

// StackBlaze: render from the running database on every request (the image is built
// once, without a database, for every deploy), so edits show on the site at once.
export const dynamic = 'force-dynamic'
