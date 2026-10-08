import { test, expect } from '@playwright/test'
import { Buffer } from 'node:buffer'

test('walk stages fit comfortably, including photo and damage report', async ({
  page,
  context,
}, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 740 })
  await context.grantPermissions(['geolocation'])
  await context.setGeolocation({ latitude: -37.81, longitude: 144.95, accuracy: 8 })
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'touchgrass_access_token',
      `${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.test`,
    )
    localStorage.clear()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => {
          throw new Error('Camera unavailable in this test')
        },
      },
    })
  })
  const destination = {
    zoneId: 'arrived',
    label: 'Flagstaff Gardens',
    center: { lat: -37.81, lng: 144.95 },
    treeCount: 40,
    density: 'High',
    bounds: { north: -37.809, south: -37.811, east: 144.951, west: 144.949 },
  }
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const path = new URL(route.request().url()).pathname
      let json: unknown = []
      if (path === '/api/sprout/route')
        json = {
          origin: { lat: -37.8183, lng: 144.9671 },
          destination,
          encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
          distanceMeters: 1000,
          durationMinutes: 12,
          denseZoneShare: 0.65,
          summaryChips: ['Leafy cover'],
          matches: [],
          steps: [],
          message: null,
        }
      if (path === '/api/sprout/areas') json = { areas: [] }
      if (path.endsWith('/facts')) json = { zoneId: 'arrived', treeCount: 40, topSpecies: [] }
      if (path === '/api/weather/now')
        json = {
          temperatureC: 21,
          band: 'mild',
          observedAt: new Date().toISOString(),
          source: 'fixture',
        }
      if (path === '/api/care/pins')
        json = {
          id: 'test-pin',
          zoneId: 'arrived',
          latitude: -37.81,
          longitude: 144.95,
          accuracyM: 8,
          hasPhoto: false,
          photoStatus: 'pending',
          createdAt: new Date().toISOString(),
          deviceToken: 'test-device-token',
        }
      if (path.endsWith('/photo'))
        json = {
          id: 'test-pin',
          latitude: -37.81,
          longitude: 144.95,
          accuracyM: 8,
          hasPhoto: true,
          photoStatus: 'pending',
        }
      if (path === '/api/care/pins/test-pin/messages') {
        const body = route.request().postDataJSON()
        json = {
          id: 'message-1',
          body: body.body,
          kind: body.kind,
          createdAt: new Date().toISOString(),
        }
      }
      await route.fulfill({ json })
    },
  )
  await page.route('**://maps.googleapis.com/**', (route) => route.abort())

  async function checkScreen(name: string) {
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true)
    expect(
      await page.locator('.pin-flow button').evaluateAll((buttons) =>
        buttons.every((button) => {
          const rect = button.getBoundingClientRect()
          return !rect.width || !rect.height || rect.height >= 44
        }),
      ),
    ).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true })
  }

  await page.goto('/')
  await page.getByRole('button', { name: 'Skip to the map' }).click()
  await page.getByRole('button', { name: 'Flinders Street Station', exact: true }).click()
  await page.getByRole('button', { name: 'Grow my route', exact: true }).click()
  await page.getByRole('button', { name: 'Start walk', exact: true }).click()
  await checkScreen('01-ready')
  await page.getByRole('button', { name: 'Walk without GPS', exact: true }).click()
  await checkScreen('02-walking')
  await page.getByRole('button', { name: 'I’ve arrived', exact: true }).click()
  await checkScreen('03-arrival')
  await page.getByRole('button', { name: 'Skip', exact: true }).click()
  await checkScreen('04-pin')
  await page.getByRole('button', { name: 'Drop a pin here', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Make this moment yours' })).toBeVisible()
  await checkScreen('05-pinned')
  await page.getByRole('button', { name: 'Take a photo of your tree', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Continue without a photo' })).toBeVisible()
  await checkScreen('06-camera')
  const photo = await page.evaluate(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 48
    canvas.height = 48
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#7fa65b'
    ctx.fillRect(0, 0, 48, 48)
    return canvas.toDataURL('image/png').split(',')[1]!
  })
  await page
    .getByLabel('Choose a tree photo')
    .setInputFiles({
      name: 'tree.png',
      mimeType: 'image/png',
      buffer: Buffer.from(photo, 'base64'),
    })
  await expect(page.getByLabel('Your message to this tree')).toBeVisible()
  expect(
    await page
      .getByLabel('Your message to this tree')
      .evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
  ).toBeGreaterThanOrEqual(16)
  await page.getByLabel('Your message to this tree').fill('A branch is hanging off.')
  await checkScreen('07-message')
  await page.getByRole('button', { name: 'Review damage report' }).click()
  await expect(page.getByRole('heading', { name: 'Damage report preview' })).toBeVisible()
  await checkScreen('08-report')
  await page.getByRole('button', { name: 'Save damage report with photo' }).click()
  await expect(page.getByRole('heading', { name: 'Your report is ready' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Share report', exact: true })).toBeHidden()
  await checkScreen('09-saved')
  await page.locator('.handoff-details > summary').click()
  await expect(page.getByRole('button', { name: 'Share report', exact: true })).toBeVisible()
  await checkScreen('10-share-options')
  await page.getByRole('button', { name: 'Next: how do you feel now?' }).click()
  await page.getByRole('button', { name: 'Calm', exact: true }).click()
  await checkScreen('11-checkin')
  await page.getByRole('button', { name: 'Log my visit' }).click()
  await expect(page.getByRole('heading', { name: '+5 leaf points' })).toBeVisible()
  await checkScreen('12-rewards')
  expect(errors).toEqual([])
})
