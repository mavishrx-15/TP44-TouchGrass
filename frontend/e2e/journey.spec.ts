import { test, expect, type Page } from '@playwright/test'

async function unlock(page: Page) {
  await page.goto('/')
  await page.getByLabel('Access password', { exact: true }).fill('touchgrass-demo')
  await page.getByRole('button', { name: 'Enter TouchGrass' }).click()
  await expect(page.getByRole('heading', { name: /Feeling overwhelmed/ })).toBeVisible()
}

test('password-only gate persists for the tab and relocks when session storage is cleared', async ({
  page,
}) => {
  await page.goto('/explore/recommendations')
  await expect(page.getByRole('heading', { name: 'Welcome to TouchGrass.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: /Areas that match/ })).toHaveCount(0)
  await page.getByLabel('Access password', { exact: true }).fill('wrong')
  await page.getByRole('button', { name: 'Enter TouchGrass' }).click()
  await expect(page.getByRole('alert')).toContainText('isn’t right')
  await page.getByLabel('Access password', { exact: true }).fill('touchgrass-demo')
  await page.getByRole('button', { name: 'Enter TouchGrass' }).click()
  await expect(page).toHaveURL(/\/explore\/recommendations$/)
  await expect(page.getByRole('heading', { name: /Areas that match/ })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: /Areas that match/ })).toBeVisible()
  await page.evaluate(() => sessionStorage.clear())
  await page.reload()
  await expect(page.getByLabel('Access password', { exact: true })).toBeVisible()
})

test('home → one route → transport → recommendations → chosen destination', async ({
  page,
}, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await unlock(page)
  await page.getByRole('button', { name: 'Find my greener route' }).click()
  await expect(page.getByRole('alert')).toContainText('Choose an address')
  await page.getByRole('button', { name: 'Kensington', exact: true }).click()
  await page.getByRole('button', { name: '15 min', exact: true }).click()
  await page.locator('#canopy').fill('90')
  await page.locator('#shade').fill('85')
  await page.getByRole('button', { name: 'Quieter surroundings', exact: true }).click()
  await page.getByRole('button', { name: 'Prefer lower-allergy areas', exact: true }).click()
  await expect(page.locator('.summary-strip')).toContainText('More tree canopy')
  await page.screenshot({ path: testInfo.outputPath('home.png'), fullPage: true })
  await page.getByRole('button', { name: 'About tree canopy' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Find my greener route' }).click()
  await expect(page.getByRole('button', { name: 'Finding your greener route' })).toBeVisible()
  await expect(page).toHaveURL(/\/explore$/)
  await expect(page.locator('.route-stats')).toHaveCount(1)
  await expect(page.getByRole('heading', { name: 'Why this route?' })).toBeVisible()
  await expect(page.locator('.why-route')).toContainText('Tree canopy')
  const walkingStats = await page.locator('.route-stats').innerText()
  const walkingTitle = await page.locator('h1').innerText()
  await page.screenshot({ path: testInfo.outputPath('route.png'), fullPage: true })
  await page.getByRole('button', { name: 'Transport', exact: true }).click()
  await expect(page.locator('.route-stats')).toContainText('Travel time')
  await expect(page.locator('.why-route')).toContainText('not used to score transport')
  await expect(page.locator('.route-matches')).toHaveCount(0)
  await page.getByRole('button', { name: 'Walking', exact: true }).click()
  await expect(page.locator('.route-stats')).toHaveText(walkingStats, { useInnerText: true })
  await page.getByRole('link', { name: 'See other options' }).click()
  await expect(page.locator('.recommendation-card')).toHaveCount(3)
  await expect(page.locator('.best-badge')).toHaveCount(1)
  await expect(page.getByRole('heading', { name: 'Area overview' })).toHaveCount(3)
  await expect(page.locator('.recommendation-card').last()).not.toContainText('Zone 0')
  await page.screenshot({ path: testInfo.outputPath('recommendations.png'), fullPage: true })
  const nextCard = page.locator('.recommendation-card').nth(1)
  const nextTitle = await nextCard.locator('h2').innerText()
  await nextCard.getByRole('button', { name: 'Navigate', exact: true }).click()
  await expect(page.locator('h1')).toHaveText(nextTitle)
  expect(nextTitle).not.toBe(walkingTitle)
  await expect(page.locator('.route-stats')).toBeVisible()
  await page.reload()
  await expect(page.locator('h1')).toHaveText(nextTitle)
  await expect(page.locator('.route-stats')).toBeVisible()
  await page.getByRole('link', { name: 'Update Preferences', exact: true }).click()
  await expect(page.getByRole('button', { name: '15 min', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('button', { name: 'Skip personalisation' }).click()
  await expect(page.locator('.summary-strip')).toHaveText('15 min walk')
  await expect(page.getByRole('textbox', { name: 'Starting location' })).toHaveValue('Kensington')
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  )
  expect(overflow).toBe(false)
  expect(errors).toEqual([])
})

test('autocomplete resolves addresses, coverage notices are conditional, and edits invalidate resolution', async ({
  page,
}) => {
  await unlock(page)
  const search = page.getByRole('textbox', { name: 'Starting location' })
  await search.fill('Geelong')
  await page.getByRole('option', { name: /Geelong Station/ }).click()
  await expect(page.locator('.coverage-notice')).toContainText('km from')
  await search.fill('unresolved address')
  await page.getByRole('button', { name: 'Find my greener route' }).click()
  await expect(page.getByRole('alert')).toContainText('Choose an address')
  await page.getByRole('button', { name: 'Kensington', exact: true }).click()
  await expect(page.locator('.coverage-notice')).toHaveCount(0)
})
