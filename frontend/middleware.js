import { createHash, timingSafeEqual } from 'node:crypto'
import { next } from '@vercel/functions'

export const config = { runtime: 'nodejs', matcher: '/:path*' }

const headers = { 'Cache-Control': 'private, no-store', Vary: 'Authorization' }

export default function middleware(request) {
  const username = process.env.SITE_AUTH_USERNAME
  const password = process.env.SITE_AUTH_PASSWORD

  // Fail closed: a missing deployment secret must never expose the site.
  if (!username || !password || username.includes(':')) {
    return new Response('Site access is not configured.', { status: 503, headers })
  }

  const authorization = request.headers.get('authorization') || ''
  const match = /^Basic ([A-Za-z0-9+/]+={0,2})$/i.exec(authorization)
  if (match) {
    const received = Buffer.from(match[1], 'base64')
    const expected = Buffer.from(`${username}:${password}`, 'utf8')
    const digest = (value) => createHash('sha256').update(value).digest()
    if (timingSafeEqual(digest(received), digest(expected))) {
      return next({ headers })
    }
  }

  return new Response('Authentication required.', {
    status: 401,
    headers: { ...headers, 'WWW-Authenticate': 'Basic realm="TouchGrass", charset="UTF-8"' },
  })
}
