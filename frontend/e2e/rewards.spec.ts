import { test, expect } from '@playwright/test'

test('prototype wardrobe unlocks once, persists and fits the screen', async ({
  page,
}, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'touchgrass_access_token',
      `${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.test`,
    )
    if (!localStorage.getItem('touchgrass.rewards.v1'))
      localStorage.setItem(
        'touchgrass.rewards.v1',
        JSON.stringify({
          points: 20,
          visits: [
            {
              zoneId: 'z1',
              label: 'Flagstaff Gardens',
              date: '2026-10-09',
              at: '2026-10-09T10:00:00Z',
              before: 'stressed',
              after: 'calm',
            },
          ],
        }),
      )
  })
  await page.goto('/rewards')
  await expect(page.getByRole('heading', { name: 'Sprout’s wardrobe' })).toBeVisible()
  await page.getByRole('button', { name: 'Autumn 15 pts' }).click()
  await page.getByRole('button', { name: 'Unlock for 15 leaf points' }).click()
  await expect(page.getByRole('status')).toContainText('Autumn Sprout unlocked')
  await expect(page.locator('.balance')).toContainText('5 leaf points')
  await page.reload()
  await expect(page.locator('.wearing')).toContainText('Sprout is wearing this skin')
  await page.getByRole('button', { name: 'Night 15 pts' }).click()
  await expect(page.getByRole('button', { name: '10 more points to unlock' })).toBeDisabled()
  await page.getByRole('button', { name: 'Autumn Wearing' }).click()
  await expect(page.getByRole('heading', { name: 'Your week in leaves' })).toBeVisible()
  await expect(page.getByText('Before · Stressed')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: testInfo.outputPath('rewards.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('walk summary follows the prototype and recommends from the reached area', async ({
  page,
}, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  if (testInfo.project.name === 'desktop') await page.setViewportSize({ width: 1440, height: 720 })
  const arrival = { lat: -37.81, lng: 144.95 }
  const nextDestination = {
    zoneId: 'next',
    label: 'Next grove',
    center: { lat: -37.8, lng: 144.99 },
    treeCount: 45,
    density: 'High',
    bounds: { north: -37.799, south: -37.801, east: 144.991, west: 144.989 },
  }
  const selectedRequests: unknown[] = []
  const requests: { origin: { lat: number; lng: number }; excludedZoneIds: string[] }[] = []
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'touchgrass_access_token',
      `${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.test`,
    )
    localStorage.setItem('touchgrass.rewards.v1', JSON.stringify({ points: 10, visits: [] }))
  })
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const path = new URL(route.request().url()).pathname
      let result: unknown = []
      if (path === '/api/sprout/route') {
        const input = route.request().postDataJSON()
        if (input.destinationZoneId) {
          selectedRequests.push(input)
          if (selectedRequests.length === 1) {
            await route.fulfill({ status: 502, json: { detail: 'Temporary route failure' } })
            return
          }
        }
        result = {
          origin: input.origin,
          destination: input.destinationZoneId
            ? nextDestination
            : {
                zoneId: 'arrived',
                label: 'Flagstaff Gardens',
                center: arrival,
                treeCount: 40,
                density: 'High',
                bounds: { north: -37.809, south: -37.811, east: 144.951, west: 144.949 },
              },
          encodedPolyline: '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
          distanceMeters: 1000,
          durationMinutes: 12,
          denseZoneShare: 0.65,
          summaryChips: ['Leafy cover'],
          matches: [],
          explanation: 'A leafy walk.',
          steps: [],
          message: null,
        }
      }
      if (path === '/api/sprout/areas') {
        requests.push(route.request().postDataJSON())
        result = {
          areas: [{ destination: nextDestination, estimatedMinutes: 5, distanceMeters: 400 }],
        }
      }
      if (path.endsWith('/facts')) result = { zoneId: 'arrived', treeCount: 40, topSpecies: [] }
      if (path === '/api/weather/now')
        result = {
          temperatureC: 21,
          band: 'mild',
          observedAt: new Date().toISOString(),
          source: 'fixture',
        }
      await route.fulfill({ json: result })
    },
  )
  await page.route('**://maps.googleapis.com/**', (route) => route.abort())
  await page.goto('/')
  await page.getByRole('button', { name: 'Skip to the map' }).click()
  await page.getByRole('button', { name: 'Flinders Street Station', exact: true }).click()
  await page.getByRole('button', { name: 'Grow my route', exact: true }).click()
  if (testInfo.project.name === 'desktop') {
    await expect
      .poll(async () => {
        const map = await page.locator('.map-mode').boundingBox()
        return Math.abs(map!.y + map!.height - page.viewportSize()!.height)
      })
      .toBeLessThan(2)
  }
  await page.getByRole('button', { name: 'Start walk', exact: true }).click()
  const panelWidth = await page.locator('.panel').evaluate((panel) => panel.clientWidth)
  await page.getByRole('button', { name: 'Walk without GPS', exact: true }).click()
  await page.getByRole('button', { name: 'I’ve arrived', exact: true }).click()
  await page.getByRole('button', { name: 'Skip', exact: true }).click()
  await page.getByRole('button', { name: 'Skip to how you feel now' }).click()
  expect(
    await page.locator('.mood-option').evaluateAll((buttons) =>
      buttons.every((button) => {
        const card = button.getBoundingClientRect()
        const label = button.querySelector('span')!.getBoundingClientRect()
        return label.left >= card.left && label.right <= card.right
      }),
    ),
  ).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('walk-checkin.png'), fullPage: true })
  await page.getByRole('button', { name: 'Calm', exact: true }).click()
  await page.getByRole('button', { name: 'Log my visit', exact: true }).click()
  await expect(page.getByRole('heading', { name: '+5 leaf points' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sprout skins' })).toBeVisible()
  expect(await page.locator('.panel').evaluate((panel) => panel.clientWidth)).toBe(panelWidth)
  await expect(page.getByRole('heading', { name: 'Your week in leaves' })).toHaveCount(0)
  await expect(page.getByRole('combobox', { name: 'Sprout’s look' })).toHaveCount(0)
  await expect.poll(() => requests.length).toBeGreaterThan(0)
  expect(requests[requests.length - 1]).toMatchObject({
    origin: arrival,
    excludedZoneIds: ['arrived'],
  })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: testInfo.outputPath('walk-summary.png'), fullPage: true })
  expect(
    await page.locator('.compact .skin-tile').evaluateAll((buttons) =>
      buttons.every((button) => {
        const card = button.getBoundingClientRect()
        const tree = button.querySelector('.sprout-tree')!.getBoundingClientRect()
        const face = button.querySelector('.tb-face')!.getBoundingClientRect()
        return (
          tree.left >= card.left &&
          tree.right <= card.right &&
          face.top >= tree.top &&
          face.bottom <= tree.bottom
        )
      }),
    ),
  ).toBe(true)
  if (testInfo.project.name === 'desktop') {
    for (const viewport of [
      { width: 1440, height: 1000 },
      { width: 1024, height: 720 },
    ]) {
      await page.setViewportSize(viewport)
      await expect
        .poll(async () => {
          const map = await page.locator('.walk-map').boundingBox()
          return Math.abs(map!.y + map!.height + 16 - viewport.height)
        })
        .toBeLessThan(2)
      expect(
        await page.evaluate(() => document.documentElement.scrollHeight <= window.innerHeight),
      ).toBe(true)
    }
  }
  await page.locator('.nearby .area').click()
  await expect(page.getByRole('alert')).toContainText('The next route could not be loaded')
  await expect(page.getByRole('heading', { name: '+5 leaf points' })).toBeVisible()
  if (testInfo.project.name === 'mobile') {
    await expect(page.locator('.walk-map')).toBeHidden()
    await page.getByRole('button', { name: 'Show map' }).click()
    await expect(page.locator('.walk-map')).toBeVisible()
    await page.getByRole('button', { name: 'Hide map' }).click()
  } else await expect(page.locator('.walk-map')).toBeVisible()
  await expect(page.getByLabel('Available leaf points')).toHaveText('15')
  await page.locator('.nearby .area').click()
  await expect(page.getByRole('heading', { name: 'Walking to Next grove' })).toBeVisible()
  expect(selectedRequests).toEqual([
    { origin: arrival, preferences: {}, destinationZoneId: 'next' },
    { origin: arrival, preferences: {}, destinationZoneId: 'next' },
  ])
})
