import assert from 'node:assert/strict'
import { test } from 'node:test'
import middleware from '../middleware.js'

test('site access protects pages and assets and fails closed', () => {
  const saved = { ...process.env }
  const request = (path, authorization) =>
    new Request(`https://example.com${path}`, {
      headers: authorization ? { authorization } : {},
    })
  const basic = (value) => `Basic ${Buffer.from(value).toString('base64')}`
  try {
    process.env.SITE_AUTH_USERNAME = 'reviewer'
    process.env.SITE_AUTH_PASSWORD = 'test-only:password'
    for (const path of ['/', '/map', '/assets/app.js', '/index.html']) {
      for (const value of [
        undefined,
        'Bearer token',
        'Basic !!!',
        basic('reviewer:wrong'),
        basic('wrong:test-only:password'),
      ]) {
        const response = middleware(request(path, value))
        assert.equal(response.status, 401)
        assert.match(response.headers.get('www-authenticate'), /^Basic /)
        assert.match(response.headers.get('cache-control'), /no-store/)
      }
      const response = middleware(request(path, basic('reviewer:test-only:password')))
      assert.equal(response.headers.get('x-middleware-next'), '1')
      assert.match(response.headers.get('cache-control'), /no-store/)
    }
    delete process.env.SITE_AUTH_PASSWORD
    assert.equal(middleware(request('/')).status, 503)
    process.env.SITE_AUTH_PASSWORD = 'test-only'
    delete process.env.SITE_AUTH_USERNAME
    assert.equal(middleware(request('/')).status, 503)
  } finally {
    for (const key of ['SITE_AUTH_USERNAME', 'SITE_AUTH_PASSWORD']) {
      if (saved[key] === undefined) delete process.env[key]
      else process.env[key] = saved[key]
    }
  }
})
